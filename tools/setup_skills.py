"""Plan selected routes and install bundled or catalog project skills, without overwrites.

This helper never downloads apps/models, starts services or edits client rules.
The agent executes the remaining setup recipes in docs/AUTO-SETUP.ru.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def plain_path(path):
    """Reject links/junctions, including ancestors of not-yet-existing paths."""
    for part in [path, *path.parents]:
        if part.is_symlink() or part.is_junction():
            raise ValueError(f'Link/junction is not supported: {part}')


def tree_hashes(path):
    plain_path(path)
    result = {}
    for item in sorted(path.iterdir()):
        plain_path(item)
        if item.is_file():
            result[item.name] = hashlib.sha256(item.read_bytes()).hexdigest()
        elif item.is_dir():
            for name, digest in tree_hashes(item).items():
                result[item.name + '/' + name] = digest
    return result


def skill_source(name):
    """Bundled skills/<name> first, then an authored entry of catalog/index.json."""
    if name != Path(name).name or name in ('.', '..'):
        raise ValueError(f'Invalid skill name: {name}')
    bundled = ROOT / 'skills' / name
    if (bundled / 'SKILL.md').is_file():
        return bundled
    index = json.loads((ROOT / 'catalog/index.json').read_text('utf-8'))
    for entry in index['skills']:
        if entry['name'] != name:
            continue
        if entry['kind'] != 'authored':
            raise ValueError(f'Third-party skill {name}: install it from upstream {entry["upstream"]}')
        plain_path(ROOT / entry['path'])
        source = (ROOT / entry['path']).resolve()
        if not source.is_relative_to((ROOT / 'catalog/skills').resolve()):
            raise ValueError(f'Catalog path escapes catalog/skills: {name}')
        if (source / 'SKILL.md').is_file():
            return source
    raise ValueError(f'Missing bundled or catalog skill: {name}')


def setup(project, client, panel, profiles, apply=False, extra_skills=()):
    if not project.is_absolute():
        raise ValueError('--project must be an absolute path')
    plain_path(project)
    project = project.resolve()
    if project == ROOT or ROOT in project.parents:
        raise ValueError('Choose a working project outside the Kit distribution')
    catalog = json.loads((ROOT / 'config/setup-profiles.json').read_text('utf-8'))
    selected = sorted(set(profiles))
    unknown = set(selected) - catalog['profiles'].keys()
    if unknown:
        raise ValueError(f'Unknown profiles: {sorted(unknown)}')
    skills = set(catalog['panel_skills'] if panel == 'tasks' else []) | set(extra_skills)
    requirements, apps, models = {'requirements.txt'}, set(), set()
    for key in selected:
        route = catalog['profiles'][key]
        skills.update(route['skills']); requirements.update(route['requirements'])
        apps.update(route['apps']); models.update(route['models'])
    clients = ['codex', 'claude'] if client == 'both' else [client]
    destinations = {'codex': '.agents/skills', 'claude': '.claude/skills'}
    operations = []
    # Preflight every destination before writing any skill. Existing differing
    # content belongs to the operator; never replace or merge it implicitly.
    for name in sorted(skills):
        source = skill_source(name)
        plain_path(source)
        hashes = tree_hashes(source)
        for target_client in clients:
            target = project / destinations[target_client] / name
            plain_path(target)
            exists = target.exists()
            if exists and (not target.is_dir() or tree_hashes(target) != hashes):
                raise ValueError(f'Existing skill differs; resolve explicitly: {target}')
            operations.append({'skill': name, 'client': target_client,
                               'source': str(source), 'target': str(target),
                               'status': 'unchanged' if exists else 'planned', 'sha256': hashes})
    for op in operations:
        if apply and op['status'] == 'planned':
            target = Path(op['target']); plain_path(target)
            shutil.copytree(op['source'], target)  # refuses a concurrent existing destination
            if tree_hashes(target) != op['sha256']:
                raise ValueError(f'Copy verification failed: {target}')
            op['status'] = 'installed'
    return {'status': 'skills_applied' if apply else 'plan', 'kit_root': str(ROOT),
            'project': str(project), 'panel': panel, 'profiles': selected,
            'requirements': sorted(requirements), 'apps': sorted(apps), 'models': sorted(models),
            'skills': operations,
            'remaining': 'Agent installs selected dependencies/apps/models and verifies real scenarios; see docs/AUTO-SETUP.ru.md'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--client', choices=['codex', 'claude', 'both'], required=True)
    parser.add_argument('--panel', choices=['tasks', 'none'], required=True)
    parser.add_argument('--profiles', nargs='*', default=[])
    parser.add_argument('--skills', nargs='*', default=[], help='Extra skills by name from catalog/index.json (see docs/SKILLS.ru.md)')
    parser.add_argument('--apply', action='store_true', help='Copy selected bundled and catalog skills into the project')
    args = parser.parse_args()
    try:
        print(json.dumps(setup(args.project, args.client, args.panel, args.profiles, args.apply, args.skills), ensure_ascii=True, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
