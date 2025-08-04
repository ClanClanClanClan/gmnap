# Reverting to Original v6 Configuration

## Reversion Steps

### 1. Restore Original Variant Map
```bash
# Backup current (broken) state
cp resources/variant_map.csv resources/variant_map.broken.csv

# Restore original
cp resources/variant_map.bak resources/variant_map.csv
```

### 2. Restore Original Converter
```bash
# Backup current state
cp src/converter.py src/converter.broken.py

# Check if we need to restore from converter_v6.py
# The current converter.py has beam search integration, so we need to revert
```

### 3. Remove Beam Search Components
```bash
# Backup beam search implementation
mv src/name_beam.py src/name_beam.broken.py
```

### 4. Restore Original Preprocessing
```bash
# The current preprocess_fixed.py keeps hyphens - need to check if original did this
# Original preprocess.py is very simple - just lowercasing and splitting
```

### 5. Key Files to Verify

**Original v6 components:**
- `converter_v6.py` - Has the working implementation
- `resources/variant_map.bak` - Original variant mappings
- `src/preprocess.py` - Simple tokenizer
- `src/segment.py` - Original segmenter

**Current (broken) components:**
- `src/converter.py` - Has beam search integration
- `resources/variant_map.csv` - Has conflicting mappings
- `src/name_beam.py` - Beam search implementation
- Various position-aware modifications

## Testing After Reversion

After reverting, we should see:
- Mathematician: ~97% (around 712/733)
- Diverse: ~80% (around 161/200)

## Safety Backup Before Changes

```bash
# Create safety backup of current state
mkdir -p backups/broken_state
cp -r src/ backups/broken_state/
cp -r resources/ backups/broken_state/
cp -r models/ backups/broken_state/

# Document current state
python3 test_accuracy.py > backups/broken_state/accuracy_before_revert.txt
```

## Questions to Resolve

1. **Should we use converter_v6.py directly or restore converter.py?**
   - converter_v6.py is from July 25 and should be the working version
   - Current converter.py has beam search calls that need removal

2. **Was the original using preprocess.py or preprocess_fixed.py?**
   - Original likely used simple preprocess.py
   - preprocess_fixed.py keeps hyphens which may be a later change

3. **Any FST model changes?**
   - Check if models/*.fst files were modified
   - Original v6 likely used the base FST models without modifications