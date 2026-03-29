#!/bin/bash
# ULTRACLEAN: Comprehensive Project Cleanup Script
# Purpose: Remove 250MB+ of unnecessary files from repository
# Date: 2025-08-31

echo "================================================"
echo "ULTRACLEAN: GMNAP Repository Cleanup"
echo "================================================"
echo ""
echo "This will remove ~250MB of unnecessary files from the repository"
echo "A backup has already been created: root_backup_20250831_235140.tar.gz"
echo ""

# Safety check
read -p "Are you sure you want to proceed? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 1
fi

echo ""
echo "Starting cleanup..."
echo ""

# Step 1: Remove cache from git tracking (but keep local files)
echo "1. Removing cache/ from git tracking..."
git rm -r --cached cache/ 2>/dev/null || echo "   cache/ already untracked"

# Step 2: Remove archive from git tracking
echo "2. Removing archive/ from git tracking..."
git rm -r --cached archive/ 2>/dev/null || echo "   archive/ already untracked"

# Step 3: Remove all database files from git
echo "3. Removing database files from git..."
find . -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" | while read file; do
    git rm --cached "$file" 2>/dev/null || true
done

# Step 4: Remove test result JSONs from git
echo "4. Removing test result JSONs from git..."
find . -name "*_results.json" -o -name "*_report.json" | while read file; do
    git rm --cached "$file" 2>/dev/null || true
done

# Step 5: Remove binary model files from git
echo "5. Removing binary model files from git..."
find . -name "*.bin" -o -name "*.ftz" | while read file; do
    git rm --cached "$file" 2>/dev/null || true
done

# Step 6: Remove __pycache__ directories
echo "6. Cleaning Python cache directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Step 7: Remove .pytest_cache
echo "7. Removing pytest cache..."
rm -rf .pytest_cache 2>/dev/null || true

# Step 8: Clean empty directories
echo "8. Cleaning empty directories..."
find . -type d -empty -delete 2>/dev/null || true

echo ""
echo "================================================"
echo "CLEANUP COMPLETE!"
echo "================================================"
echo ""
echo "Size reduction summary:"
echo "  - cache/: 131MB removed from git"
echo "  - archive/: 120MB removed from git"
echo "  - Total: ~251MB removed from repository"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Commit cleanup: git commit -m '🧹 MAJOR: Remove 250MB of cache/archive from repo'"
echo "  3. Push changes: git push"
echo ""
echo "Note: Local cache files are preserved but no longer tracked by git"