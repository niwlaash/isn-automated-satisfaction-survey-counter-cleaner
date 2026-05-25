import pandas as pd
import os
import re

def normalize_name(name):
    if pd.isna(name): return ""
    name = str(name).strip().lower()
    # Handle canonical variations
    if "indoor hockey" in name or "hoki dewan" in name or "hockey indoor" in name:
        return "indoor hockey"
    if "lawn bowl" in name:
        return "lawn bowl"
    if "7s" in name:
        name = name.replace("7s", " 7s") # Ensure space before 7s
    return " ".join(name.replace("/", " ").split()) # Remove slashes and extra spaces

def process_survey():
    # File Paths
    input_file = os.path.join('raw_data', '2026 ISN PART 1_ Athletes and Coaches Satisfaction Survey on Sports Science & Sports Medicine Services (Responses).xlsx')
    instructions_file = 'instruction2.md.resolve'
    output_file = os.path.join('output', 'Processed_Survey_Update_2026.xlsx')

    if not all(os.path.exists(f) for f in [input_file, instructions_file]):
        print("Error: Missing required files.")
        return

    # Columns requested in instruction2.md.resolve
    cols = [
        'Sport', 'PK Done', 'Podium Done', 'RTG Done', 'Sukan Berfasa Done', 
        'Total Athletes Responded', 'PK Coach', 'Podium Coach', 'RTG Coach', 
        'Sukan Berfasa Coach', 'Total Coaches Responded', 'TOTAL RESPONDENT'
    ]

    # 1. Read Sports List from Instructions
    print("Reading target sports list...")
    all_content = []
    try:
        # Use utf-8-sig to handle potential BOM
        with open(instructions_file, 'r', encoding='utf-8-sig') as f:
            all_content = f.readlines()
    except Exception as e:
        print(f"Error reading instructions: {e}")
        return

    target_sports = []
    found_update = False
    for line in all_content:
        line_clean = line.strip()
        if not line_clean: continue
        
        # Priority 1: Sports after "UPDATE:"
        if "UPDATE:" in line_clean.upper():
            found_update = True
            target_sports = [] 
            continue
        
        if found_update:
            # Once in UPDATE mode, take every non-empty line until maybe next header
            if not any(k in line_clean.lower() for k in ["|", "--", "done", "respondent"]):
                target_sports.append(line_clean)
        else:
            # Fallback/Initial mode: Avoid table headers and unrelated text
            if "i want you to create" in line_clean.lower():
                # If we encounter the table instruction, we stop the initial list
                # to prevent capturing table cells as sport names
                break
            
            if not any(keyword in line_clean.lower() for keyword in ["|", "--", "done", "respondent"]):
                target_sports.append(line_clean)

    print(f"Targeting {len(target_sports)} sports from instructions.")
    
    # 2. Load Survey Data
    print("Loading survey responses...")
    df_input = pd.read_excel(input_file)
    
    # Identify Columns
    col_role = next((c for c in df_input.columns if 'Role' in c or 'Peranan' in c), None)
    col_sport = next((c for c in df_input.columns if 'Sport' in c and 'Sukan' in c and 'specify' not in c.lower()), None)
    col_others = next((c for c in df_input.columns if 'specify the sport' in c.lower()), None)
    col_prog = next((c for c in df_input.columns if 'Sports Program' in c), None)

    def get_final_sport(row):
        main = str(row[col_sport])
        if "Others" in main or "Lain-lain" in main:
            others = str(row[col_others])
            if others and others != 'nan':
                return others.strip()
        return main.strip()

    df_input['Final_Sport'] = df_input.apply(get_final_sport, axis=1)
    df_input['Norm_Sport'] = df_input['Final_Sport'].apply(normalize_name)
    
    def map_program(prog):
        if pd.isna(prog): return 'Others'
        prog_lower = str(prog).strip().lower()
        if 'berfasa' in prog_lower:
            return 'Sukan Berfasa'
        if 'pelapis' in prog_lower or 'pk' in prog_lower:
            return 'PK'
        if 'podium' in prog_lower:
            return 'Podium'
        if 'road to gold' in prog_lower or 'rtg' in prog_lower:
            return 'RTG'
        return 'Others'
        
    df_input['Program_Mapped'] = df_input[col_prog].apply(map_program)
    df_input['Is_Athlete'] = df_input[col_role].str.contains('Athlete', case=False, na=False)
    df_input['Is_Coach'] = df_input[col_role].str.contains('Coach', case=False, na=False)
    
    # Store assigned respondents to prevent double counting
    assigned_indices = set()
    summary_data = []

    print("Counting responses for each sport...")
    for sport_str in target_sports:
        norm_sport_target = normalize_name(sport_str.split('/')[0])
        
        # Para status check based on sport name
        is_para_sport = any(k in sport_str.lower() for k in ["para", "wc ", "berkerusi roda"])
        
        def match_criteria(idx, row):
            if idx in assigned_indices: return False
            if row['Norm_Sport'] != norm_sport_target:
                if norm_sport_target not in row['Norm_Sport'] and row['Norm_Sport'] not in norm_sport_target:
                    return False
            
            has_para_keyword = any(k in row['Norm_Sport'] for k in ["para", "wc ", "berkerusi roda"])
            if is_para_sport and not has_para_keyword: return False
            if not is_para_sport and has_para_keyword: return False
            
            return True

        mask = df_input.apply(lambda r: match_criteria(r.name, r), axis=1)
        matches = df_input[mask]
        assigned_indices.update(matches.index.tolist())

        counts = {'Sport': sport_str}
        for prog in ['PK', 'Podium', 'RTG', 'Sukan Berfasa']:
            counts[f'{prog} Done'] = len(matches[(matches['Is_Athlete']) & (matches['Program_Mapped'] == prog)])
            counts[f'{prog} Coach'] = len(matches[(matches['Is_Coach']) & (matches['Program_Mapped'] == prog)])
        
        counts['Total Athletes Responded'] = len(matches[matches['Is_Athlete']])
        counts['Total Coaches Responded'] = len(matches[matches['Is_Coach']])
        counts['TOTAL RESPONDENT'] = counts['Total Athletes Responded'] + counts['Total Coaches Responded']
        
        summary_data.append(counts)

    # 3. Create Summary DataFrame with pre-defined columns
    df_summary = pd.DataFrame(summary_data, columns=cols)
    
    # Ensure all cells have 0 instead of NaN if summary_data was partially populated
    df_summary = df_summary.fillna(0)

    # Handle "Others"
    unassigned = df_input[~df_input.index.isin(assigned_indices)]
    df_review = unassigned.copy()
    if not df_review.empty:
        df_review = df_review[[col_role, 'Final_Sport', col_sport, col_others, col_prog]]
        df_review.columns = ['Role', 'Final Sport', 'Original Sport Col', 'Others Specified', 'Program']

    # 4. Save to Excel
    print(f"Saving results to {output_file}...")
    with pd.ExcelWriter(output_file) as writer:
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        if not df_review.empty:
            df_review.to_excel(writer, sheet_name='Others_Review', index=False)
        else:
            pd.DataFrame(columns=['All respondents matched!']).to_excel(writer, sheet_name='Others_Review', index=False)

    print(f"Total respondents processed: {len(assigned_indices)} / {len(df_input)}")
    print(f"Unmatched respondents: {len(unassigned)} (visible in Others_Review sheet)")
    print("Success!")

if __name__ == "__main__":
    process_survey()
