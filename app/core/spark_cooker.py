import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher


def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower().strip())


def similarity(a, b):
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def parse_ontology(content):
    projects = {}
    current_project = None
    current_section = None
    current_list = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("### PROJECT:"):
            if current_project and current_section:
                projects[current_project][current_section] = current_list
            current_project = line.replace("### PROJECT:", "").strip()
            projects[current_project] = {}
            current_section = None
            current_list = []
        elif line.startswith("### ") and current_project:
            if current_section and current_list:
                projects[current_project][current_section] = current_list
            current_section = line.replace("### ", "").strip().rstrip(":")
            current_list = []
        elif line.startswith("- ") and current_project and current_section:
            current_list.append(line[2:].strip())
    if current_project and current_section and current_list:
        projects[current_project][current_section] = current_list
    return projects


def cluster_items(items_list, threshold=0.75):
    clusters = []
    for run_idx, items in enumerate(items_list):
        for item in items:
            found_cluster = False
            for cluster in clusters:
                rep = cluster['phrasings'].most_common(1)[0][0]
                if similarity(item, rep) >= threshold:
                    cluster['phrasings'][item] += 1
                    cluster['runs'].add(run_idx)
                    found_cluster = True
                    break
            if not found_cluster:
                clusters.append({'phrasings': Counter([item]), 'runs': {run_idx}})
    return clusters


def cook_section(section_name, all_runs_items, total_runs, fire_threshold=0.6, weak_threshold=0.4):
    clusters = cluster_items(all_runs_items)
    cooked_items = []
    for cluster in clusters:
        canonical = cluster['phrasings'].most_common(1)[0][0]
        run_count = len(cluster['runs'])
        depth = run_count / total_runs
        if depth >= fire_threshold:
            status = "FIRE"
        elif depth >= weak_threshold:
            status = "WEAK"
        else:
            status = "BUNK"
        cooked_items.append({'text': canonical, 'depth': depth, 'runs': run_count, 'status': status, 'variants': list(cluster['phrasings'].keys())})
    cooked_items.sort(key=lambda x: -x['depth'])
    return cooked_items


def generate_canonical_output(all_cooked):
    lines = []
    for project_name, sections in all_cooked.items():
        lines.append(f"### PROJECT: {project_name}")
        if 'STAGE' in sections and sections['STAGE']:
            lines.append(f"### STAGE: {sections['STAGE'][0]['text']}")
            lines.append("")
        for section_name in ['GOALS', 'TECH_STACK', 'ENTITIES', 'DECISIONS', 'RISKS', 'ACTION_ITEMS']:
            if section_name not in sections or not sections[section_name]:
                continue
            lines.append(f"### {section_name}:")
            for item in sections[section_name]:
                if item['status'] == 'BUNK':
                    continue
                prefix = "[WEAK] " if item['status'] == 'WEAK' else ""
                lines.append(f"- {prefix}{item['text']}")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def generate_report(all_cooked, total_runs):
    lines = []
    lines.append("=" * 70)
    lines.append("SPARK COOKER REPORT")
    lines.append("=" * 70)
    lines.append(f"Runs cooked: {total_runs}")
    lines.append("")
    total_fire = total_weak = total_bunk = 0
    for project_name, sections in all_cooked.items():
        lines.append(f"🔥 PROJECT: {project_name}")
        lines.append("")
        for section_name, items in sections.items():
            if not items:
                continue
            fire = sum(1 for i in items if i['status'] == 'FIRE')
            weak = sum(1 for i in items if i['status'] == 'WEAK')
            bunk = sum(1 for i in items if i['status'] == 'BUNK')
            total_fire += fire; total_weak += weak; total_bunk += bunk
            lines.append(f"  {section_name}: FIRE={fire} WEAK={weak} BUNK={bunk}")
            for item in items:
                emoji = "🔥" if item['status'] == 'FIRE' else "🟡" if item['status'] == 'WEAK' else "🗑️"
                lines.append(f"    {emoji} [{item['runs']}/{total_runs}] {item['text'][:60]}")
            lines.append("")
    lines.append("=" * 70)
    lines.append("COOKER SUMMARY")
    lines.append("=" * 70)
    total = total_fire + total_weak + total_bunk
    lock_score = round((total_fire / total) * 100, 1) if total else 0
    lines.append(f"Total concepts: {total}")
    lines.append(f"FIRE: {total_fire} ({round(total_fire/total*100,1) if total else 0}%)")
    lines.append(f"WEAK: {total_weak} ({round(total_weak/total*100,1) if total else 0}%)")
    lines.append(f"BUNK: {total_bunk} ({round(total_bunk/total*100,1) if total else 0}%)")
    lines.append(f"Lock Score: {lock_score}%")
    lines.append("")
    if lock_score >= 85:
        lines.append("DIAGNOSIS: Ready to move. Package the product.")
    elif lock_score >= 60:
        lines.append("DIAGNOSIS: Mostly locked. Weak items need more chat.")
    else:
        lines.append("DIAGNOSIS: Not ready. Too much bunk. Keep talking.")
    return "\n".join(lines), lock_score, total_fire, total_weak, total_bunk


def cook_spark_outputs(outputs_list, fire_threshold=0.6, weak_threshold=0.4):
    total_runs = len(outputs_list)
    parsed = [parse_ontology(output) for output in outputs_list]
    all_projects = defaultdict(lambda: defaultdict(list))
    for run_idx, projects in enumerate(parsed):
        for project_name, sections in projects.items():
            for section_name, items in sections.items():
                all_projects[project_name][section_name].append(items)
    all_cooked = {}
    for project_name, section_data in all_projects.items():
        all_cooked[project_name] = {}
        for section_name, all_runs_items in section_data.items():
            all_cooked[project_name][section_name] = cook_section(section_name, all_runs_items, total_runs, fire_threshold, weak_threshold)
    canonical_text = generate_canonical_output(all_cooked)
    report_text, lock_score, fire_count, weak_count, bunk_count = generate_report(all_cooked, total_runs)
    return {'canonical_text': canonical_text, 'report_text': report_text, 'lock_score': lock_score, 'fire_count': fire_count, 'weak_count': weak_count, 'bunk_count': bunk_count, 'all_cooked': all_cooked}
