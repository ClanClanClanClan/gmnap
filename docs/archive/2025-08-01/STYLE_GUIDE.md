# Korean Regional Processor v7 – Style Guide

## Typography & Punctuation (§7)

### Dashes and Hyphens
- **ASCII minus (-)**: Use in code, data files, and command-line options
  - `--build-fsts`, `-0.8`, `utf-8-sig`
- **EN dash (–)**: Use for numeric ranges and connections in prose
  - "94.27%–97.00%", "Korean–English conversion", "2020–2025"
- **EM dash (—)**: Use for parenthetical remarks in prose
  - "The system performs well — exceeding all targets — across datasets"

### Quotation Marks
- **Code and filenames**: Use straight quotes
  - `"rr_syllable_map.csv"`, `grep "pattern"`
- **Prose quotations**: Use typographer's quotes
  - "The system demonstrates excellent performance"
- **Nested quotes**: "The log shows 'validation passed' successfully"

### Capitalization
- **Headings**: Title Case for Main Headings
- **Sentences**: Sentence case for body text and subheadings
- **Technical terms**: 
  - FST (not Fst or fst) when referring to finite-state transducers
  - "bidirectional FST system" (sentence case in prose)
  - "PyNini library" (preserve proper names)

## Unicode Handling

### Timestamps (§1.7)
- **Standard format**: ISO-8601 Zulu time
  - ✅ `2025-07-31T10:15:30Z`
  - ❌ `20250731_101530` (ambiguous timezone)

### Character Encoding (§4.4)
- **CSV files**: Use `utf-8-sig` to handle Windows BOM
- **JSON logs**: Use `utf-8` with `ensure_ascii=False`
- **Documentation**: Use `utf-8` consistently

### Unicode Normalization
- **Korean text**: NFC normalization for Hangul
- **Roman text**: Case-fold and normalize spacing
- **Weight values**: Strip Unicode whitespace categories

## Code Style

### Weight Format (§1.4, §4.1)
- **Pattern**: `^-?\d+\.\d{1,4}$`
- **Examples**: 
  - ✅ `-0.8`, `1.2345`, `0.0`
  - ❌ `-.8` (no leading zero), `-0.8 ` (trailing space)
- **Semantics**: Positive costs = -log(probability), lower = preferred

### CSV Structure
- **Comments**: Lines starting with `#`
- **Format**: `hangul,roman,weight`
- **No trailing commas**: Each row exactly 3 fields
- **Categories**: Group related mappings with comment headers

### JSON Logs (§1.6)
- **Schema validation**: Required for all improvement logs
- **Timestamps**: ISO-8601 Zulu format
- **Checksums**: SHA-256 for reproducibility
- **No PII**: Hash sensitive data in production (§6.1)

## Documentation Standards

### Technical Writing
- **Conciseness**: Favor clarity over elaboration
- **Consistency**: Use established terminology throughout
- **Examples**: Provide concrete examples for abstract concepts
- **Cross-references**: Link related sections and findings

### Error Messages
- **Actionable**: Include specific steps to resolve
- **Context**: Show what was expected vs. actual
- **Categorized**: Group by error type for easier diagnosis

### Performance Reporting
- **Precision**: Report accuracy to 2 decimal places
- **Context**: Always include sample size (N/Total format)
- **Confidence**: Include Wilson score bounds for statistical validity
- **Comparison**: Show baseline vs. current performance

## Version Control

### Commit Messages
- **SIF changes**: Prefix with "SIF:" for systematic improvements
- **Format**: "SIF: Add Korean mathematician surnames (+3 cases)"
- **Rationale**: Include brief justification in body

### File Permissions (§1.2, §3.5)
- **Mapping file**: `chmod 444` (read-only) except during SIF operations
- **Audit logs**: `chmod 644` (owner write, others read)
- **Backups**: `chmod 600` (owner only)

### Branch Protection
- **Pre-receive hooks**: Server-side validation required
- **Matrix testing**: Ubuntu + Windows compatibility
- **Timeout**: 5-minute maximum for CI pipelines

## Configuration Management

### YAML Structure
- **Hierarchical**: Group related settings logically
- **Comments**: Document non-obvious parameters
- **Defaults**: Provide sensible fallback values
- **Validation**: Schema validation for production configs

### Environment Variables
- **Naming**: `KOREAN_PROCESSOR_*` prefix
- **Secrets**: Use secure secret management, never in code
- **Overrides**: Allow config.yaml overrides via environment

## Security & Privacy (§6)

### PII Handling
- **Production**: Hash names in logs using Blake2b + daily salt
- **Development**: Raw names acceptable for debugging
- **Retention**: Automatic cleanup of old audit logs
- **Access**: Principle of least privilege

### Audit Trail
- **Cryptographic**: SHA-256 checksums for integrity
- **Immutable**: Append-only audit logs
- **Searchable**: JSON structure for programmatic analysis
- **Compliant**: GDPR/privacy regulation adherence

## Performance Standards

### Accuracy Targets
- **Production minimum**: 85% (GMNAP v7 requirement)
- **Current achievement**: 94.54% across 1,098 test cases
- **Monitoring**: Daily health checks with alerting

### Statistical Validation
- **Confidence**: 95% Wilson score intervals required
- **Regression**: No more than 0.5 standard errors decline
- **Significance**: Changes must exceed measurement uncertainty

### Response Time
- **Individual names**: < 10ms per conversion
- **Batch processing**: < 1s per 100 names
- **FST compilation**: < 30s for full rebuild

---

*Style Guide v1.0 – Korean Regional Processor v7*  
*Addresses audit findings §7.1–§7.14 for consistent documentation*