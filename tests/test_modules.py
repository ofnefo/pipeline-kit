"""Portable production checks with synthetic/local data; no external services."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from datetime import date
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    result=importlib.util.module_from_spec(spec)
    sys.modules[name]=result
    spec.loader.exec_module(result)
    return result

def run(*args):
    return subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,capture_output=True,text=True,
                          encoding='utf-8',errors='replace',timeout=60,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

class ProductionTests(unittest.TestCase):
    def test_estimate_reconciles_and_flags_explicit_difference(self):
        engine=module('kit_estimate','modules/office/scripts/estimate_engine.py')
        data=json.loads((ROOT/'examples/estimate.json').read_text())
        result=engine.calculate(data,as_of=date(2026,1,1))
        self.assertEqual(result['financial_result']['net_profit'],Decimal('198.00'))
        self.assertEqual(result['financial_result']['estimate_total'],Decimal('600.00'))
        self.assertEqual(result['warnings'],[])
        data['items'][0]['amount']='601.00'
        self.assertTrue(any('differs' in w for w in engine.calculate(data)['warnings']))
        data['items'][0]['quantity']='NaN'
        with self.assertRaises(ValueError):engine.calculate(data)

    def test_composition_dimensions_pixels_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/'sample.png';proof=Path(td)/'proof.png'
            args=('modules/design/scripts/compose_layers.py','--spec','examples/composition.json',
                  '--output',output,'--proof',proof)
            result=run(*args)
            self.assertEqual(result.returncode,0,result.stderr)
            before=output.read_bytes()
            with Image.open(output) as image:
                self.assertEqual(image.size,(640,360))
                self.assertEqual(image.getpixel((320,180)),(229,193,124,255))
            self.assertTrue(proof.is_file())
            self.assertNotEqual(run(*args).returncode,0)
            self.assertEqual(output.read_bytes(),before)

    def test_offline_html_and_utm(self):
        seo=module('kit_seo','modules/web/scripts/seo_growth.py')
        self.assertEqual(seo.audit((ROOT/'examples/page.html').read_text())['findings'],[])
        self.assertTrue(seo.audit('<html><img src="a.png"></html>')['findings'])
        url=seo.utm('https://example.com/?a=1&utm_source=old#section','new','two words','test')
        self.assertIn('a=1',url);self.assertIn('utm_campaign=two+words',url)
        self.assertNotIn('old',url);self.assertTrue(url.endswith('#section'))
        with self.assertRaises(ValueError):seo.utm('https://user:pass@example.com','a','b','c')

    def test_office_initialization_and_doctor(self):
        with tempfile.TemporaryDirectory() as td:
            result=run('modules/office/scripts/office_project.py','init','--workspace',td,
                       '--code','sample','--name','Sample project')
            self.assertEqual(result.returncode,0,result.stderr)
            project=Path(result.stdout.strip())
            self.assertTrue((project/'OFFICE_PROJECT.json').is_file())
            doctor=run('modules/office/scripts/office_project.py','doctor','--project',project,'--json')
            self.assertNotIn('Traceback',doctor.stderr)
            self.assertIsInstance(json.loads(doctor.stdout),dict)
            self.assertIn(doctor.returncode,(0,1,2))

    def test_print_regressions(self):
        result=run('modules/design/scripts/test_preflight_print.py')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Ran 5 tests',result.stderr)

    def test_production_command_entrypoints(self):
        commands={
            'office':['office_project','estimate_engine','document_inventory','extract_source','prepare_proposal'],
            'design':['compose_layers','inspect_assets','make_contact_sheet','preflight_print'],
            'video':['editorial','montage'],
            'music':['master_audio','lyric_preflight','ru_pronunciation'],
            'web':['seo_growth'],
        }
        for kind,names in commands.items():
            for name in names:
                with self.subTest(command=name):
                    result=run(f'modules/{kind}/scripts/{name}.py','--help')
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn('usage:',result.stdout.lower())

    @unittest.skipUnless(importlib.util.find_spec('jsonschema'),'Optional office environment not installed')
    def test_office_optional_entrypoints(self):
        for name in ('receipt_adapter','ttn'):
            with self.subTest(command=name):
                result=run(f'modules/office/scripts/{name}.py','--help')
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('usage:',result.stdout.lower())

if __name__=='__main__':unittest.main()
