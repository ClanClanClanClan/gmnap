"""
Next-Generation Analytics for GMNAP V7
Predictive analytics, real-time insights, and intelligent decision support
"""

import asyncio
import json
import logging
import time
import numpy as np
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set, Callable
from enum import Enum
import uuid
import statistics

# ML and analytics imports (graceful fallback)
try:
    from sklearn.ensemble import RandomForestRegressor, IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    import pandas as pd
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False


class AnalyticsLevel(Enum):
    """Analytics sophistication levels"""
    BASIC = "basic"
    ADVANCED = "advanced"
    PREDICTIVE = "predictive"
    REAL_TIME = "real_time"
    AI_ENHANCED = "ai_enhanced"


class MetricType(Enum):
    """Types of metrics to track"""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    USAGE = "usage"
    ERRORS = "errors"
    SECURITY = "security"
    BUSINESS = "business"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class MetricDataPoint:
    """Individual metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """System alert"""
    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    threshold: float
    actual_value: float
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class AnalyticsInsight:
    """Generated analytical insight"""
    insight_id: str
    type: str  # trend, anomaly, prediction, recommendation
    title: str
    description: str
    confidence: float
    impact_score: float
    generated_at: datetime
    data_sources: List[str]
    recommendations: List[str] = field(default_factory=list)


class PredictiveAnalyticsEngine:
    """
    Advanced Predictive Analytics Engine
    
    Features:
    - Real-time metric collection and analysis
    - Anomaly detection using isolation forests
    - Time series forecasting with multiple models
    - Automated insight generation
    - Intelligent alerting with dynamic thresholds
    - Performance optimization recommendations
    - Capacity planning and scaling predictions
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Data storage
        self.metrics_buffer = deque(maxlen=10000)  # Recent metrics
        self.historical_data = defaultdict(list)   # Long-term storage
        self.metric_metadata = {}
        
        # Models
        self.prediction_models = {}
        self.anomaly_detectors = {}
        self.scalers = {}
        
        # Analytics state
        self.alerts = []
        self.insights = []
        self.thresholds = {}
        
        # Real-time processing
        self.streaming_processors = {}
        self.alert_rules = {}
        
        # Performance tracking
        self.analysis_performance = {
            'predictions_made': 0,
            'anomalies_detected': 0,
            'insights_generated': 0,
            'alerts_triggered': 0
        }
        
        self.logger.info(f"PredictiveAnalyticsEngine initialized")
        if not ML_AVAILABLE:
            self.logger.warning("scikit-learn not available. Predictive features will be limited.")
    
    async def ingest_metric(self, metric: MetricDataPoint):
        """Ingest a new metric data point"""
        # Add to buffer
        self.metrics_buffer.append(metric)
        
        # Add to historical data
        self.historical_data[metric.metric_name].append(metric)
        
        # Update metadata
        if metric.metric_name not in self.metric_metadata:
            self.metric_metadata[metric.metric_name] = {
                'first_seen': metric.timestamp,
                'count': 0,
                'min_value': float('inf'),
                'max_value': float('-inf'),
                'tags': set()
            }
        
        meta = self.metric_metadata[metric.metric_name]
        meta['count'] += 1
        meta['last_seen'] = metric.timestamp
        meta['min_value'] = min(meta['min_value'], metric.value)
        meta['max_value'] = max(meta['max_value'], metric.value)
        meta['tags'].update(metric.tags.keys())
        
        # Real-time analysis
        await self._process_real_time_metric(metric)
    
    async def _process_real_time_metric(self, metric: MetricDataPoint):
        """Process metric in real-time for alerts and anomalies"""
        # Check for anomalies
        is_anomaly = await self._detect_anomaly(metric)
        if is_anomaly:
            await self._handle_anomaly(metric)
        
        # Check alert rules
        await self._evaluate_alert_rules(metric)
        
        # Update streaming processors
        for processor_name, processor in self.streaming_processors.items():
            try:
                await processor(metric)
            except Exception as e:
                self.logger.error(f"Streaming processor {processor_name} failed: {e}")
    
    async def _detect_anomaly(self, metric: MetricDataPoint) -> bool:
        """Detect if metric value is anomalous"""
        if not ML_AVAILABLE:
            return await self._basic_anomaly_detection(metric)
        
        metric_name = metric.metric_name
        
        # Get or create anomaly detector
        if metric_name not in self.anomaly_detectors:
            await self._create_anomaly_detector(metric_name)
        
        detector = self.anomaly_detectors.get(metric_name)
        if not detector:
            return False
        
        try:
            # Prepare feature vector
            features = self._prepare_anomaly_features(metric)
            
            # Detect anomaly
            anomaly_score = detector.decision_function([features])[0]
            is_anomaly = detector.predict([features])[0] == -1
            
            if is_anomaly:
                self.logger.info(f"Anomaly detected for {metric_name}: {metric.value} (score: {anomaly_score:.3f})")
                self.performance_tracking['anomalies_detected'] += 1
            
            return is_anomaly
            
        except Exception as e:
            self.logger.error(f"Anomaly detection failed for {metric_name}: {e}")
            return False
    
    async def _basic_anomaly_detection(self, metric: MetricDataPoint) -> bool:
        """Basic anomaly detection using statistical methods"""
        metric_name = metric.metric_name
        recent_values = [m.value for m in self.historical_data[metric_name][-100:]]  # Last 100 values
        
        if len(recent_values) < 10:
            return False
        
        # Calculate z-score
        mean_val = statistics.mean(recent_values)
        std_val = statistics.stdev(recent_values)
        
        if std_val == 0:
            return False
        
        z_score = abs((metric.value - mean_val) / std_val)
        return z_score > 3.0  # 3-sigma rule
    
    def _prepare_anomaly_features(self, metric: MetricDataPoint) -> List[float]:
        """Prepare feature vector for anomaly detection"""
        features = [metric.value]
        
        # Add time-based features
        features.append(metric.timestamp.hour)
        features.append(metric.timestamp.weekday())
        
        # Add recent trend features
        metric_name = metric.metric_name
        recent_values = [m.value for m in self.historical_data[metric_name][-10:]]
        
        if len(recent_values) >= 3:
            # Recent average
            features.append(statistics.mean(recent_values))
            
            # Recent trend (simple slope)
            x = list(range(len(recent_values)))
            y = recent_values
            if len(x) > 1:
                slope = (sum(x[i] * y[i] for i in range(len(x))) * len(x) - sum(x) * sum(y)) / \
                       (sum(x[i]**2 for i in range(len(x))) * len(x) - sum(x)**2)
                features.append(slope)
        
        return features
    
    async def _create_anomaly_detector(self, metric_name: str):
        """Create anomaly detector for a metric"""
        if not ML_AVAILABLE:
            return
        
        historical_values = self.historical_data[metric_name]
        if len(historical_values) < 50:  # Need minimum data
            return
        
        # Prepare training data
        training_features = []
        for metric in historical_values:
            features = self._prepare_anomaly_features(metric)
            training_features.append(features)
        
        # Create and train detector
        detector = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        
        try:
            detector.fit(training_features)
            self.anomaly_detectors[metric_name] = detector
            self.logger.info(f"Created anomaly detector for {metric_name}")
        except Exception as e:
            self.logger.error(f"Failed to create anomaly detector for {metric_name}: {e}")
    
    async def _handle_anomaly(self, metric: MetricDataPoint):
        """Handle detected anomaly"""
        # Generate alert
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            severity=AlertSeverity.WARNING,
            title=f"Anomaly detected in {metric.metric_name}",
            description=f"Value {metric.value} is anomalous for {metric.metric_name}",
            metric_name=metric.metric_name,
            threshold=0.0,  # Not threshold-based
            actual_value=metric.value,
            timestamp=metric.timestamp
        )
        
        self.alerts.append(alert)
        self.performance_tracking['alerts_triggered'] += 1
        
        # Generate insight
        insight = AnalyticsInsight(
            insight_id=str(uuid.uuid4()),
            type="anomaly",
            title=f"Anomalous behavior in {metric.metric_name}",
            description=f"Detected unusual pattern in {metric.metric_name} metric",
            confidence=0.8,
            impact_score=self._calculate_anomaly_impact(metric),
            generated_at=datetime.utcnow(),
            data_sources=[metric.metric_name],
            recommendations=[
                "Investigate root cause",
                "Check system resources", 
                "Review recent changes"
            ]
        )
        
        self.insights.append(insight)
        self.performance_tracking['insights_generated'] += 1
    
    def _calculate_anomaly_impact(self, metric: MetricDataPoint) -> float:
        """Calculate impact score for anomaly"""
        # Simple heuristic based on metric type and deviation
        base_impact = 0.5
        
        # Adjust based on metric name
        if 'error' in metric.metric_name.lower():
            base_impact += 0.3
        elif 'performance' in metric.metric_name.lower():
            base_impact += 0.2
        elif 'security' in metric.metric_name.lower():
            base_impact += 0.4
        
        return min(1.0, base_impact)
    
    async def _evaluate_alert_rules(self, metric: MetricDataPoint):
        """Evaluate alert rules for a metric"""
        metric_name = metric.metric_name
        
        if metric_name not in self.alert_rules:
            return
        
        for rule in self.alert_rules[metric_name]:
            if self._rule_matches(metric, rule):
                await self._trigger_alert(metric, rule)
    
    def _rule_matches(self, metric: MetricDataPoint, rule: Dict[str, Any]) -> bool:
        """Check if metric matches alert rule"""
        threshold = rule['threshold']
        operator = rule.get('operator', 'gt')  # gt, lt, eq, ne
        
        if operator == 'gt':
            return metric.value > threshold
        elif operator == 'lt':
            return metric.value < threshold
        elif operator == 'eq':
            return abs(metric.value - threshold) < 1e-6
        elif operator == 'ne':
            return abs(metric.value - threshold) > 1e-6
        
        return False
    
    async def _trigger_alert(self, metric: MetricDataPoint, rule: Dict[str, Any]):
        """Trigger alert based on rule"""
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            severity=AlertSeverity(rule.get('severity', 'warning')),
            title=rule.get('title', f"Threshold exceeded for {metric.metric_name}"),
            description=rule.get('description', f"Metric {metric.metric_name} exceeded threshold"),
            metric_name=metric.metric_name,
            threshold=rule['threshold'],
            actual_value=metric.value,
            timestamp=metric.timestamp
        )
        
        self.alerts.append(alert)
        self.performance_tracking['alerts_triggered'] += 1
    
    async def predict_metric(self, metric_name: str, horizon_minutes: int = 60) -> Optional[Dict[str, Any]]:
        """Predict future values for a metric"""
        if not ML_AVAILABLE:
            return await self._basic_prediction(metric_name, horizon_minutes)
        
        # Get or create prediction model
        if metric_name not in self.prediction_models:
            await self._create_prediction_model(metric_name)
        
        model = self.prediction_models.get(metric_name)
        if not model:
            return None
        
        try:
            # Prepare features for prediction
            features = self._prepare_prediction_features(metric_name, horizon_minutes)
            if not features:
                return None
            
            # Make prediction
            predicted_values = model.predict(features)
            
            # Calculate confidence intervals (simplified)
            confidence_interval = self._calculate_confidence_interval(metric_name, predicted_values)
            
            self.performance_tracking['predictions_made'] += len(predicted_values)
            
            return {
                'metric_name': metric_name,
                'horizon_minutes': horizon_minutes,
                'predictions': predicted_values.tolist(),
                'confidence_interval': confidence_interval,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Prediction failed for {metric_name}: {e}")
            return None
    
    async def _basic_prediction(self, metric_name: str, horizon_minutes: int) -> Optional[Dict[str, Any]]:
        """Basic prediction using simple trend analysis"""
        recent_values = [m.value for m in self.historical_data[metric_name][-20:]]
        
        if len(recent_values) < 5:
            return None
        
        # Simple linear trend
        x = list(range(len(recent_values)))
        y = recent_values
        
        # Calculate trend
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i]**2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
        intercept = (sum_y - slope * sum_x) / n
        
        # Generate predictions
        predictions = []
        for i in range(1, horizon_minutes // 5 + 1):  # Every 5 minutes
            future_x = len(recent_values) + i
            predicted_value = slope * future_x + intercept
            predictions.append(predicted_value)
        
        return {
            'metric_name': metric_name,
            'horizon_minutes': horizon_minutes,
            'predictions': predictions,
            'confidence_interval': {'lower': 0.9, 'upper': 1.1},  # Mock confidence
            'generated_at': datetime.utcnow().isoformat()
        }
    
    async def _create_prediction_model(self, metric_name: str):
        """Create prediction model for a metric"""
        if not ML_AVAILABLE:
            return
        
        historical_values = self.historical_data[metric_name]
        if len(historical_values) < 100:  # Need sufficient data
            return
        
        # Prepare training data
        features, targets = self._prepare_training_data(metric_name)
        
        if len(features) < 50:
            return
        
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            train_predictions = model.predict(X_train_scaled)
            test_predictions = model.predict(X_test_scaled)
            
            train_mae = mean_absolute_error(y_train, train_predictions)
            test_mae = mean_absolute_error(y_test, test_predictions)
            test_r2 = r2_score(y_test, test_predictions)
            
            self.logger.info(f"Created prediction model for {metric_name}: "
                           f"MAE={test_mae:.3f}, R2={test_r2:.3f}")
            
            # Store model and scaler
            self.prediction_models[metric_name] = model
            self.scalers[metric_name] = scaler
            
        except Exception as e:
            self.logger.error(f"Failed to create prediction model for {metric_name}: {e}")
    
    def _prepare_training_data(self, metric_name: str) -> Tuple[List[List[float]], List[float]]:
        """Prepare training data for prediction model"""
        historical_values = self.historical_data[metric_name]
        
        features = []
        targets = []
        
        # Create sliding window features
        window_size = 10
        prediction_steps = 1
        
        for i in range(window_size, len(historical_values) - prediction_steps):
            # Features: last N values + time features
            feature_vector = []
            
            # Historical values
            for j in range(window_size):
                feature_vector.append(historical_values[i - window_size + j].value)
            
            # Time features
            current_metric = historical_values[i]
            feature_vector.extend([
                current_metric.timestamp.hour,
                current_metric.timestamp.weekday(),
                current_metric.timestamp.day
            ])
            
            features.append(feature_vector)
            
            # Target: value after prediction_steps
            targets.append(historical_values[i + prediction_steps].value)
        
        return features, targets
    
    def _prepare_prediction_features(self, metric_name: str, horizon_minutes: int) -> Optional[List[List[float]]]:
        """Prepare features for making predictions"""
        historical_values = self.historical_data[metric_name]
        
        if len(historical_values) < 10:
            return None
        
        # Use last 10 values as base features
        features = []
        base_feature = []
        
        # Add historical values
        for metric in historical_values[-10:]:
            base_feature.append(metric.value)
        
        # Add time features for future predictions
        current_time = datetime.utcnow()
        steps = horizon_minutes // 5  # Predict every 5 minutes
        
        for step in range(1, steps + 1):
            future_time = current_time + timedelta(minutes=step * 5)
            feature_vector = base_feature.copy()
            feature_vector.extend([
                future_time.hour,
                future_time.weekday(),
                future_time.day
            ])
            features.append(feature_vector)
        
        return features
    
    def _calculate_confidence_interval(self, metric_name: str, predictions: np.ndarray) -> Dict[str, float]:
        """Calculate confidence interval for predictions"""
        # Simplified confidence interval based on historical variance
        historical_values = [m.value for m in self.historical_data[metric_name][-100:]]
        
        if len(historical_values) < 10:
            return {'lower': 0.9, 'upper': 1.1}
        
        std_dev = statistics.stdev(historical_values)
        confidence_factor = 1.96  # 95% confidence interval
        
        return {
            'lower': float(np.mean(predictions) - confidence_factor * std_dev),
            'upper': float(np.mean(predictions) + confidence_factor * std_dev)
        }
    
    async def generate_insights(self) -> List[AnalyticsInsight]:
        """Generate analytical insights from collected data"""
        insights = []
        
        # Trend analysis insights
        trend_insights = await self._analyze_trends()
        insights.extend(trend_insights)
        
        # Performance insights
        performance_insights = await self._analyze_performance()
        insights.extend(performance_insights)
        
        # Capacity planning insights
        capacity_insights = await self._analyze_capacity()
        insights.extend(capacity_insights)
        
        # Quality insights
        quality_insights = await self._analyze_quality()
        insights.extend(quality_insights)
        
        self.insights.extend(insights)
        self.performance_tracking['insights_generated'] += len(insights)
        
        return insights
    
    async def _analyze_trends(self) -> List[AnalyticsInsight]:
        """Analyze trends in metrics"""
        insights = []
        
        for metric_name, values in self.historical_data.items():
            if len(values) < 20:
                continue
            
            recent_values = [m.value for m in values[-20:]]
            older_values = [m.value for m in values[-40:-20]] if len(values) >= 40 else []
            
            if not older_values:
                continue
            
            recent_avg = statistics.mean(recent_values)
            older_avg = statistics.mean(older_values)
            
            change_percent = ((recent_avg - older_avg) / older_avg) * 100 if older_avg != 0 else 0
            
            if abs(change_percent) > 20:  # Significant trend
                trend_type = "increasing" if change_percent > 0 else "decreasing"
                
                insight = AnalyticsInsight(
                    insight_id=str(uuid.uuid4()),
                    type="trend",
                    title=f"{metric_name} is {trend_type}",
                    description=f"{metric_name} has {trend_type} by {abs(change_percent):.1f}% recently",
                    confidence=min(0.9, abs(change_percent) / 100),
                    impact_score=min(1.0, abs(change_percent) / 50),
                    generated_at=datetime.utcnow(),
                    data_sources=[metric_name],
                    recommendations=self._generate_trend_recommendations(metric_name, trend_type, change_percent)
                )
                
                insights.append(insight)
        
        return insights
    
    def _generate_trend_recommendations(self, metric_name: str, trend_type: str, change_percent: float) -> List[str]:
        """Generate recommendations based on trends"""
        recommendations = []
        
        if 'error' in metric_name.lower():
            if trend_type == "increasing":
                recommendations.extend([
                    "Investigate error sources",
                    "Review recent code changes",
                    "Check system stability"
                ])
        elif 'performance' in metric_name.lower():
            if trend_type == "decreasing":
                recommendations.extend([
                    "Optimize system performance",
                    "Consider scaling resources",
                    "Review system bottlenecks"
                ])
        elif 'usage' in metric_name.lower():
            if trend_type == "increasing" and abs(change_percent) > 30:
                recommendations.extend([
                    "Plan for capacity scaling",
                    "Monitor resource utilization",
                    "Consider load balancing"
                ])
        
        return recommendations
    
    async def _analyze_performance(self) -> List[AnalyticsInsight]:
        """Analyze system performance patterns"""
        insights = []
        
        # Look for performance degradation patterns
        performance_metrics = [name for name in self.historical_data.keys() 
                             if 'response_time' in name or 'latency' in name]
        
        for metric_name in performance_metrics:
            values = self.historical_data[metric_name]
            if len(values) < 50:
                continue
            
            recent_values = [m.value for m in values[-24:]]  # Last 24 data points
            baseline_values = [m.value for m in values[-100:-50]]  # Baseline
            
            if not baseline_values:
                continue
            
            recent_p95 = sorted(recent_values)[int(0.95 * len(recent_values))]
            baseline_p95 = sorted(baseline_values)[int(0.95 * len(baseline_values))]
            
            if recent_p95 > baseline_p95 * 1.5:  # 50% degradation
                insight = AnalyticsInsight(
                    insight_id=str(uuid.uuid4()),
                    type="performance",
                    title=f"Performance degradation in {metric_name}",
                    description=f"95th percentile {metric_name} has increased by {((recent_p95/baseline_p95-1)*100):.1f}%",
                    confidence=0.8,
                    impact_score=0.9,
                    generated_at=datetime.utcnow(),
                    data_sources=[metric_name],
                    recommendations=[
                        "Investigate performance bottlenecks",
                        "Review system resources",
                        "Consider performance optimization"
                    ]
                )
                
                insights.append(insight)
        
        return insights
    
    async def _analyze_capacity(self) -> List[AnalyticsInsight]:
        """Analyze capacity and scaling needs"""
        insights = []
        
        # Analyze resource utilization trends
        resource_metrics = [name for name in self.historical_data.keys() 
                          if any(keyword in name.lower() for keyword in ['cpu', 'memory', 'disk', 'usage'])]
        
        for metric_name in resource_metrics:
            values = self.historical_data[metric_name]
            if len(values) < 20:
                continue
            
            recent_values = [m.value for m in values[-10:]]
            avg_utilization = statistics.mean(recent_values)
            
            if avg_utilization > 80:  # High utilization
                # Predict when capacity will be exceeded
                prediction = await self.predict_metric(metric_name, 240)  # 4 hours ahead
                
                capacity_insight = AnalyticsInsight(
                    insight_id=str(uuid.uuid4()),
                    type="capacity",
                    title=f"High {metric_name} utilization",
                    description=f"{metric_name} is at {avg_utilization:.1f}% utilization",
                    confidence=0.9,
                    impact_score=min(1.0, avg_utilization / 100),
                    generated_at=datetime.utcnow(),
                    data_sources=[metric_name],
                    recommendations=[
                        "Scale resources proactively",
                        "Monitor capacity trends",
                        "Consider load distribution"
                    ]
                )
                
                insights.append(capacity_insight)
        
        return insights
    
    async def _analyze_quality(self) -> List[AnalyticsInsight]:
        """Analyze data and process quality"""
        insights = []
        
        # Analyze error rates and success patterns
        error_metrics = [name for name in self.historical_data.keys() 
                        if 'error' in name.lower() or 'failure' in name.lower()]
        
        for metric_name in error_metrics:
            values = self.historical_data[metric_name]
            if len(values) < 10:
                continue
            
            recent_values = [m.value for m in values[-10:]]
            avg_error_rate = statistics.mean(recent_values)
            
            if avg_error_rate > 5:  # Error rate above 5%
                quality_insight = AnalyticsInsight(
                    insight_id=str(uuid.uuid4()),
                    type="quality",
                    title=f"High error rate in {metric_name}",
                    description=f"{metric_name} error rate is {avg_error_rate:.1f}%",
                    confidence=0.9,
                    impact_score=min(1.0, avg_error_rate / 20),
                    generated_at=datetime.utcnow(),
                    data_sources=[metric_name],
                    recommendations=[
                        "Investigate error sources",
                        "Improve error handling",
                        "Review data quality"
                    ]
                )
                
                insights.append(quality_insight)
        
        return insights
    
    def add_alert_rule(self, metric_name: str, threshold: float, severity: str = "warning", 
                      operator: str = "gt", title: str = None, description: str = None):
        """Add a new alert rule"""
        if metric_name not in self.alert_rules:
            self.alert_rules[metric_name] = []
        
        rule = {
            'threshold': threshold,
            'severity': severity,
            'operator': operator,
            'title': title or f"Threshold alert for {metric_name}",
            'description': description or f"{metric_name} exceeded threshold"
        }
        
        self.alert_rules[metric_name].append(rule)
        self.logger.info(f"Added alert rule for {metric_name}: {rule}")
    
    def add_streaming_processor(self, name: str, processor: Callable):
        """Add a streaming processor for real-time analysis"""
        self.streaming_processors[name] = processor
        self.logger.info(f"Added streaming processor: {name}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        current_time = datetime.utcnow()
        
        # Recent metrics summary
        recent_metrics = {}
        for metric_name, values in self.historical_data.items():
            if values:
                latest = values[-1]
                recent_metrics[metric_name] = {
                    'current_value': latest.value,
                    'timestamp': latest.timestamp.isoformat(),
                    'trend': self._calculate_short_term_trend(values)
                }
        
        # Active alerts
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        
        # Recent insights
        recent_insights = sorted(self.insights, key=lambda x: x.generated_at, reverse=True)[:10]
        
        return {
            'timestamp': current_time.isoformat(),
            'metrics_count': len(self.historical_data),
            'recent_metrics': recent_metrics,
            'active_alerts': len(active_alerts),
            'alert_breakdown': {
                severity.value: len([a for a in active_alerts if a.severity == severity])
                for severity in AlertSeverity
            },
            'recent_insights': [
                {
                    'type': insight.type,
                    'title': insight.title,
                    'confidence': insight.confidence,
                    'impact_score': insight.impact_score,
                    'generated_at': insight.generated_at.isoformat()
                }
                for insight in recent_insights
            ],
            'performance': self.analysis_performance,
            'models_trained': len(self.prediction_models),
            'anomaly_detectors': len(self.anomaly_detectors)
        }
    
    def _calculate_short_term_trend(self, values: List[MetricDataPoint]) -> str:
        """Calculate short-term trend for a metric"""
        if len(values) < 5:
            return "stable"
        
        recent_values = [m.value for m in values[-5:]]
        
        # Simple slope calculation
        x = list(range(len(recent_values)))
        y = recent_values
        
        n = len(x)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x = sum(x)
        sum_y = sum(y)
        sum_x2 = sum(x[i]**2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
        
        if abs(slope) < 0.1:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"
    
    async def export_insights_report(self, format: str = "json") -> str:
        """Export comprehensive insights report"""
        report_data = {
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {
                'total_metrics': len(self.historical_data),
                'total_insights': len(self.insights),
                'active_alerts': len([a for a in self.alerts if not a.resolved]),
                'models_trained': len(self.prediction_models)
            },
            'insights_by_type': {},
            'top_insights': [],
            'recommendations': set()
        }
        
        # Group insights by type
        for insight in self.insights:
            if insight.type not in report_data['insights_by_type']:
                report_data['insights_by_type'][insight.type] = []
            report_data['insights_by_type'][insight.type].append({
                'title': insight.title,
                'confidence': insight.confidence,
                'impact_score': insight.impact_score
            })
        
        # Top insights by impact
        top_insights = sorted(self.insights, key=lambda x: x.impact_score, reverse=True)[:10]
        report_data['top_insights'] = [
            {
                'title': insight.title,
                'type': insight.type,
                'confidence': insight.confidence,
                'impact_score': insight.impact_score,
                'recommendations': insight.recommendations
            }
            for insight in top_insights
        ]
        
        # Collect all unique recommendations
        for insight in self.insights:
            report_data['recommendations'].update(insight.recommendations)
        
        report_data['recommendations'] = list(report_data['recommendations'])
        
        if format == "json":
            return json.dumps(report_data, indent=2, default=str)
        else:
            # Could implement other formats (CSV, PDF, etc.)
            return json.dumps(report_data, indent=2, default=str)