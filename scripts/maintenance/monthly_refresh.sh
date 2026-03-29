#!/bin/bash
# Monthly corpus refresh cron job
# Add to crontab: 0 0 1 * * /path/to/monthly_refresh.sh

# Set working directory
cd /app/gmnap

# Load environment
source .venv/bin/activate

# Log start
echo "$(date): Starting monthly corpus refresh" >> logs/corpus_refresh.log

# Run refresh script
python scripts/refresh_corpus.py --validate 2>&1 | tee -a logs/corpus_refresh.log

# Check if refresh was successful
if [ $? -eq 0 ]; then
    echo "$(date): Corpus refresh completed successfully" >> logs/corpus_refresh.log
    
    # Run overfitting check
    python scripts/anti_overfitting_monitor.py 2>&1 | tee -a logs/overfitting_check.log
    
    # Restart service to pick up changes
    systemctl restart gmnap-korea || docker restart gmnap-korea
    
else
    echo "$(date): Corpus refresh FAILED" >> logs/corpus_refresh.log
    # Send alert (optional)
    # curl -X POST "https://alerts.example.com/webhook" -d "Corpus refresh failed"
fi

echo "$(date): Monthly refresh process completed" >> logs/corpus_refresh.log