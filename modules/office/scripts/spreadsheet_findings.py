"""Localized read-only heuristics over existing Office workbook cells; no recalculation.

Formula-level checks follow the audit-xls checklist (anthropics/financial-services, Apache-2.0):
errors, hardcoded literals, neighbour patterns, SUM boundaries, pasted-over formulas, broken and
self references, hidden content. Model-integrity checks are the Decimal oracle in project_checks."""
import re
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET
import project_checks as quality

CELL=re.compile(r'^([A-Z]{1,3})([1-9][0-9]*)$')
REFERENCE=re.compile(r'(\$?)([A-Z]{1,3})(\$?)([1-9][0-9]*)(?![A-Z0-9_(])')
REF_TOKEN=re.compile(r"(?<![\w.$'\]!])(?:(?:'((?:[^']|'')+)'|([^\W\d][\w.]*))!)?(\$?[A-Z]{1,3}\$?[1-9][0-9]*)(?::(\$?[A-Z]{1,3}\$?[1-9][0-9]*))?(?![\w(])")
LITERAL=re.compile(r'(?<![\w.])(\d+(?:\.\d*)?(?:E[+-]?\d+)?)(?![\w.(])')
STRING=re.compile(r'"(?:[^"]|"")*"')
EXTERNAL=re.compile(r'\[\d+\]')

def coordinate(value):
    m=CELL.fullmatch(value)
    if not m: raise ValueError('Invalid A1 reference: '+str(value))
    col=0
    for char in m[1]: col=26*col+ord(char)-64
    row=int(m[2])
    if col>16384 or row>1048576: raise ValueError('Cell exceeds XLSX limits')
    return col,row

def pattern(formula,cell):
    if not formula or any(c in formula for c in ['"','[',']','!']): return None
    col,row=coordinate(cell)
    def replace(m):
        c,r=coordinate(m[2]+m[4])
        return f'C{c if m[1] else c-col}{"A" if m[1] else "R"}R{r if m[3] else r-row}{"A" if m[3] else "R"}'
    return REFERENCE.sub(replace,formula.upper().replace(' ',''))

def sheet_names(workbook):
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(workbook) as archive:
        root=ET.fromstring(archive.read('xl/workbook.xml'))
    return [s.attrib['name'] for s in root.findall('s:sheets/s:sheet',ns)]

def references(formula):
    """Yield (sheet or None, first cell, last cell) for A1 references; external [n] links are skipped."""
    for m in REF_TOKEN.finditer(STRING.sub('""',formula)):
        sheet=m[1].replace("''","'") if m[1] is not None else m[2]
        if sheet and sheet.startswith('['): continue
        yield sheet,m[3].replace('$',''),(m[4] or m[3]).replace('$','')

def literals(formula):
    """Numeric constants typed into a formula (audit-xls: hardcodes inside formulas); 0 and 1 are structural."""
    rest=STRING.sub(' ',formula.upper())
    rest=REF_TOKEN.sub(' ',EXTERNAL.sub(' ',rest.replace('#REF!',' ')))
    rest=re.sub(r'\$?[A-Z]{1,3}:\$?[A-Z]{1,3}|\$?[0-9]+:\$?[0-9]+',' ',rest)
    if re.search(r'ROUND|TRUNC|FIXED',rest): rest=re.sub(r',\s*-?[0-9]\s*\)',')',rest)
    found=[]
    for m in LITERAL.finditer(rest):
        try:
            if Decimal(m[1]) not in (0,1): found.append(m[1])
        except InvalidOperation:
            pass
    return found

def structural(workbook, cells, add):
    names={n.casefold():n for n in sheet_names(workbook)}
    hidden={}
    for (sheet,cell),value in cells.items():
        if value.get('hidden') and (value['formula'] or value['value'] is not None):
            hidden.setdefault(sheet,[]).append(cell)
        text=value.get('formula_text')
        if not text: continue
        if '#REF!' in text.upper(): add('broken_reference','error',sheet,cell,{'formula':text})
        if EXTERNAL.search(STRING.sub('""',text)): add('external_link','info',sheet,cell,{'formula':text})
        col,row=coordinate(cell)
        for ref_sheet,first,last in references(text.replace('#REF!',' ')):
            if ref_sheet is not None and ref_sheet.casefold() not in names:
                add('unknown_sheet_reference','error',sheet,cell,{'formula':text,'sheet_reference':ref_sheet}); continue
            if ref_sheet is None or names[ref_sheet.casefold()]==sheet:
                (c1,r1),(c2,r2)=coordinate(first),coordinate(last)
                if min(c1,c2)<=col<=max(c1,c2) and min(r1,r2)<=row<=max(r1,r2):
                    add('self_reference','error',sheet,cell,{'formula':text,'reference':first if first==last else first+':'+last})
    for sheet,refs in sorted(hidden.items()):
        add('hidden_content','info',sheet,None,{'cells':len(refs),'sample':refs[:10],'note':'Hidden rows, columns or sheet may hold overrides'})

def audit(workbook, mapping, cells=None):
    if cells is None: cells,_=quality.workbook_cells(workbook)
    findings=[]
    def add(code,severity,sheet,cell,evidence):
        findings.append({'code':code,'severity':severity,'sheet':sheet,'cell_or_range':cell,'evidence':evidence,'automatic_repair':False})
    for (sheet,cell),value in cells.items():
        if value['type']=='e': add('formula_error','error',sheet,cell,{'stored_error':value['value']})
        if value['formula'] and value['value'] is None: add('cache_absent','error',sheet,cell,{'formula':value.get('formula_text')})
        if value['formula'] and value.get('formula_kind') not in {None,'normal'}:
            add('formula_kind_not_checked','info',sheet,cell,{'kind':value['formula_kind']})
    if any(v['formula'] for v in cells.values()):
        add('cache_freshness_unverified','info',None,None,{'workbook_sha256':quality.digest(workbook),'recalculated':False,'note':'Stored caches only; use existing hash-bound recalculation QA.'})
    try:
        structural(workbook,cells,add)
    except (KeyError,ValueError,zipfile.BadZipFile,ET.ParseError) as exc:
        add('structure_not_checked','warning',None,None,{'error':str(exc)})
    for entry in mapping.get('checks',[]):
        if not isinstance(entry,dict): continue
        key=(entry.get('sheet'),entry.get('cell'))
        if entry.get('formula',True) and key in cells and not cells[key]['formula']:
            add('formula_replaced_by_constant','error',*key,{'value':cells[key]['value'],'expected_formula':True,'oracle':entry.get('oracle')})
    rules=mapping.get('audit',{})
    intentional={}
    try:
        if not isinstance(rules,dict) or set(rules)-{'sum_ranges','formula_groups','inputs','intentional_constants','cache_workbook_sha256'}:
            raise ValueError('Unknown audit fields or invalid audit object')
        if rules.get('cache_workbook_sha256') is not None and rules['cache_workbook_sha256']!=quality.digest(workbook):
            add('cache_evidence_stale','error',None,None,{'declared':rules['cache_workbook_sha256'],'actual':quality.digest(workbook)})
        for entry in rules.get('intentional_constants',[]):
            coordinate(entry['cell'])
            if not isinstance(entry['reason'],str) or not entry['reason'].strip(): raise ValueError('Intentional constant requires a reason')
            intentional[(entry['sheet'],entry['cell'])]=entry['reason']
        for entry in rules.get('sum_ranges',[]):
            key=(entry['sheet'],entry['cell'])
            coordinate(key[1])
            expected=entry['range'].upper().replace('$','')
            if expected.count(':')!=1: raise ValueError('Expected one rectangular SUM range')
            start,end=map(coordinate,expected.split(':'))
            if start[0]>end[0] or start[1]>end[1]: raise ValueError('Reversed SUM range')
            value=cells.get(key)
            formula=(value or {}).get('formula_text') or ''
            m=re.fullmatch(r'SUM\((\$?[A-Z]+\$?[1-9][0-9]*:\$?[A-Z]+\$?[1-9][0-9]*)\)',formula.upper().replace(' ',''))
            if not m:
                add('sum_range_not_checked','warning',*key,{'expected_range':expected,'formula':formula,'reason':'Only a direct single-range SUM is supported'})
            elif m[1].replace('$','') != expected:
                add('sum_boundary_mismatch','error',*key,{'expected_range':expected,'actual_range':m[1],'formula':formula})
        for group in rules.get('formula_groups',[]):
            sheet=group['sheet']
            refs=group['cells']
            if not isinstance(refs,list) or len(refs)<3 or len(set(refs))!=len(refs): raise ValueError('Formula group requires at least three unique cells')
            patterns={}
            for ref in refs:
                coordinate(ref)
                value=cells.get((sheet,ref))
                if not value: add('group_cell_missing','warning',sheet,ref,{'group':refs}); continue
                if not value['formula']:
                    reason=intentional.get((sheet,ref))
                    add('intentional_constant' if reason else 'group_constant','info' if reason else 'warning',sheet,ref,{'reason':reason,'value':value['value'],'group':refs})
                    continue
                patterns[ref]=pattern(value.get('formula_text'),ref) if value.get('formula_kind') in {None,'normal'} else None
                if patterns[ref] is None: add('pattern_not_checked','info',sheet,ref,{'formula':value.get('formula_text')})
            counts=Counter(p for p in patterns.values() if p is not None)
            if counts:
                majority,count=counts.most_common(1)[0]
                if count>=2 and count>sum(counts.values())/2:
                    for ref,p in patterns.items():
                        if p is not None and p!=majority:
                            add('neighbor_formula_pattern','warning',sheet,ref,{'pattern':p,'majority_pattern':majority,'group':refs})
        for entry in rules.get('inputs',[]):
            key=(entry['sheet'],entry['cell'])
            coordinate(key[1])
            value=cells.get(key)
            if value is None: add('input_missing','error',*key,{'expected':entry['expected']}); continue
            if value['formula']: add('input_is_formula','warning',*key,{'formula':value.get('formula_text')}); continue
            actual=value.get('text_value') if value.get('text_value') is not None else value['value']
            try:
                equal=quality.decimal(actual,'input')==quality.decimal(entry['expected'],'expected')
            except (ValueError,InvalidOperation):
                add('input_not_numeric','error',*key,{'actual':actual,'expected':entry['expected']}); continue
            if not equal:
                add('hidden_input_override' if value.get('hidden') else 'input_override','warning',*key,{'actual':actual,'expected':entry['expected'],'hidden':value.get('hidden',False)})
            elif value.get('text_value') is not None:
                add('numeric_text_input','info',*key,{'actual':actual,'normalized':str(quality.decimal(actual,'input')),'note':'Excel may treat this as text; no cell was converted'})
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        add('audit_config_invalid','error',None,None,{'error':str(exc)})
    for (sheet,cell),value in cells.items():
        text=value.get('formula_text')
        if not text or (sheet,cell) in intentional: continue
        found=literals(text)
        if found: add('formula_hardcoded_literal','warning',sheet,cell,{'formula':text,'literals':found,'note':'Move the constant to a labelled input cell or declare it in audit.intentional_constants'})
    return findings
