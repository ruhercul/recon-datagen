"""Validate 1:N match generation."""
import sys
sys.path.insert(0, 'src')

from recon_datagen.models import GenerationConfig
from recon_datagen.scenarios import get_scenario
from recon_datagen.generator import DataGenerator
from collections import defaultdict

config = GenerationConfig(
    scenario='bank-recon',
    total_source_rows=100,
    match_percent=0.60,
    potential_percent=0.25,
    one_to_n_ratio=0.30,
    min_n_splits=2,
    max_n_splits=5,
    output_path='test.xlsx',
    seed=42
)

scenario = get_scenario('bank-recon')
scenario = type(scenario)(seed=42)
generator = DataGenerator(scenario, config)

all_source = []
all_target = []

for source_chunk, target_chunk in generator.generate():
    all_source.extend(source_chunk)
    all_target.extend(target_chunk)

stats = generator.stats

print('='*60)
print('GENERATION STATISTICS')
print('='*60)
print(f'Source rows: {stats.source_rows}')
print(f'Target rows: {stats.target_rows}')
print()
print('MATCH BREAKDOWN:')
print(f'  Matched exact 1:1: {stats.exact_1_to_1_matches}')
print(f'  Potential 1:N aggregate: {stats.exact_1_to_n_matches}')
print(f'  Potential matches total: {stats.potential_matches}')
print(f'  Unmatched source:  {stats.unmatched_source}')
print(f'  Unmatched target:  {stats.unmatched_target}')
print()

# Calculate expected values
expected_exact = int(100 * 0.60)
expected_potential = int(100 * 0.25)
expected_1_to_n = int(expected_potential * 0.30)

print('EXPECTED vs ACTUAL:')
print(f'  Expected matched exact 1:1: {expected_exact}, Actual: {stats.exact_1_to_1_matches}')
print(f'  Expected potential 1:N: {expected_1_to_n}, Actual: {stats.exact_1_to_n_matches}')
print(f'  Expected potential total: {expected_potential}, Actual: {stats.potential_matches}')
print(f'  Expected unmatched: {int(100 * 0.15)}, Actual: {stats.unmatched_source}')
print()

# Validate 1:N ratio
if stats.potential_matches > 0:
    actual_1_to_n_ratio = stats.exact_1_to_n_matches / stats.potential_matches
    print('1:N RATIO VALIDATION:')
    print(f'  Configured 1:N ratio of potential matches: 30%')
    print(f'  Actual 1:N ratio: {actual_1_to_n_ratio*100:.1f}%')
    print(f'  Within tolerance: {abs(actual_1_to_n_ratio - 0.30) < 0.05}')
print()

# Group targets by exact reference. Finance.Copilot groups 1:N records by
# identical mapping keys; target keys are no longer suffixed per split.
print('='*60)
print('VALIDATING 1:N MATCH AMOUNTS SUM CORRECTLY')
print('='*60)

target_by_ref = defaultdict(list)
for t in all_target:
    ref = t.get('BankReference', '')
    target_by_ref[ref].append(t)

# Find 1:N examples
one_to_n_examples = [
    (source.get('DocumentNumber'), target_by_ref[source.get('DocumentNumber')])
    for source in all_source
    if len(target_by_ref[source.get('DocumentNumber')]) > 1
]

print(f'Found {len(one_to_n_examples)} 1:N match groups')
print()

# Show first 5 examples
for i, (ref, targets) in enumerate(one_to_n_examples[:5]):
    source_match = next((s for s in all_source if s.get('DocumentNumber') == ref), None)
    
    if source_match:
        source_amt = source_match.get('Amount', 0)
        target_sum = sum(t.get('BankAmount', 0) for t in targets)
        
        print(f'Example {i+1}: {ref}')
        print(f'  Source Amount: ${source_amt:,.2f}')
        print(f'  Target Records: {len(targets)}')
        for j, t in enumerate(targets):
            print(f'    Target {j+1}: ${t.get("BankAmount", 0):,.2f}')
        print(f'  Target Sum: ${target_sum:,.2f}')
        print(f'  Match: {abs(source_amt - target_sum) < 0.01}')
        print()

# Validate ALL 1:N matches
print('='*60)
print('FINAL VALIDATION')
print('='*60)
all_valid = True
for ref, targets in one_to_n_examples:
    source_match = next((s for s in all_source if s.get('DocumentNumber') == ref), None)
    if source_match:
        source_amt = source_match.get('Amount', 0)
        target_sum = sum(t.get('BankAmount', 0) for t in targets)
        if abs(source_amt - target_sum) >= 0.01:
            print(f'MISMATCH: {ref} - Source: {source_amt}, Target Sum: {target_sum}')
            all_valid = False

if all_valid:
    print(f'SUCCESS: All {len(one_to_n_examples)} 1:N matches have correct amount sums!')
