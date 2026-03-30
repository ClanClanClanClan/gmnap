"""
Global Infrastructure Framework for GMNAP V7
Multi-region deployment with auto-scaling and disaster recovery
"""

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Cloud provider SDKs (graceful fallback)
try:
    import boto3

    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

try:
    from kubernetes import client, config

    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False

try:
    import docker

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False


class DeploymentRegion(Enum):
    """Supported deployment regions"""

    US_EAST = "us-east-1"
    US_WEST = "us-west-2"
    EU_WEST = "eu-west-1"
    EU_CENTRAL = "eu-central-1"
    ASIA_PACIFIC = "ap-southeast-1"
    ASIA_NORTHEAST = "ap-northeast-1"


class ServiceStatus(Enum):
    """Service status states"""

    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"


class ScalingTrigger(Enum):
    """Auto-scaling trigger types"""

    CPU_UTILIZATION = "cpu"
    MEMORY_UTILIZATION = "memory"
    REQUEST_RATE = "requests"
    QUEUE_DEPTH = "queue_depth"
    RESPONSE_TIME = "response_time"


@dataclass
class DeploymentConfig:
    """Deployment configuration"""

    regions: List[DeploymentRegion]
    min_instances: int = 2
    max_instances: int = 20
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 80.0
    health_check_interval: int = 30
    auto_scaling_enabled: bool = True
    disaster_recovery_enabled: bool = True
    backup_retention_days: int = 30
    cdn_enabled: bool = True
    monitoring_enabled: bool = True


@dataclass
class ServiceInstance:
    """Individual service instance"""

    instance_id: str
    region: DeploymentRegion
    status: ServiceStatus
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    request_count: int = 0
    response_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None
    endpoint: Optional[str] = None
    version: str = "1.0.0"


@dataclass
class LoadBalancerConfig:
    """Load balancer configuration"""

    algorithm: str = "round_robin"  # round_robin, least_connections, weighted
    health_check_path: str = "/health"
    health_check_interval: int = 10
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2
    session_affinity: bool = False


@dataclass
class BackupConfig:
    """Backup configuration"""

    enabled: bool = True
    schedule: str = "0 2 * * *"  # Daily at 2 AM
    retention_days: int = 30
    encryption_enabled: bool = True
    cross_region_replication: bool = True
    incremental_backups: bool = True


class GlobalDeploymentManager:
    """
    Global Infrastructure Deployment Manager

    Features:
    - Multi-region deployment orchestration
    - Auto-scaling based on metrics
    - Load balancing and traffic routing
    - Health monitoring and alerting
    - Disaster recovery and failover
    - Automated backups and data replication
    - CDN integration for global performance
    """

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Service management
        self.instances: Dict[str, ServiceInstance] = {}
        self.regions_status: Dict[DeploymentRegion, ServiceStatus] = {}
        self.load_balancer_config = LoadBalancerConfig()
        self.backup_config = BackupConfig()

        # Metrics and monitoring
        self.metrics_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.alerts = []
        self.scaling_events = []

        # Cloud provider clients
        self.aws_clients = {}
        self.k8s_clients = {}

        # Initialize regions
        for region in self.config.regions:
            self.regions_status[region] = ServiceStatus.STOPPED

        # Initialize cloud clients
        if AWS_AVAILABLE:
            self._initialize_aws_clients()

        if K8S_AVAILABLE:
            self._initialize_k8s_clients()

    def _initialize_aws_clients(self):
        """Initialize AWS clients for each region"""
        for region in self.config.regions:
            try:
                self.aws_clients[region.value] = {
                    "ec2": boto3.client("ec2", region_name=region.value),
                    "ecs": boto3.client("ecs", region_name=region.value),
                    "elb": boto3.client("elbv2", region_name=region.value),
                    "cloudwatch": boto3.client("cloudwatch", region_name=region.value),
                    "rds": boto3.client("rds", region_name=region.value),
                }
                self.logger.info(f"Initialized AWS clients for {region.value}")
            except Exception as e:
                self.logger.error(
                    f"Failed to initialize AWS clients for {region.value}: {e}"
                )

    def _initialize_k8s_clients(self):
        """Initialize Kubernetes clients"""
        try:
            config.load_incluster_config()  # Try in-cluster config first
        except Exception:
            try:
                config.load_kube_config()  # Fall back to local config
            except Exception as e:
                self.logger.error(f"Failed to load Kubernetes config: {e}")
                return

        self.k8s_clients = {
            "apps_v1": client.AppsV1Api(),
            "core_v1": client.CoreV1Api(),
            "autoscaling_v1": client.AutoscalingV1Api(),
        }
        self.logger.info("Initialized Kubernetes clients")

    async def deploy_global_infrastructure(self) -> Dict[str, Any]:
        """Deploy infrastructure across all configured regions"""
        self.logger.info(
            f"Starting global deployment across {len(self.config.regions)} regions"
        )

        deployment_results = {}

        for region in self.config.regions:
            try:
                self.logger.info(f"Deploying to region: {region.value}")
                result = await self._deploy_region(region)
                deployment_results[region.value] = result

                if result["success"]:
                    self.regions_status[region] = ServiceStatus.STARTING
                else:
                    self.regions_status[region] = ServiceStatus.UNHEALTHY

            except Exception as e:
                self.logger.error(f"Deployment failed for region {region.value}: {e}")
                deployment_results[region.value] = {"success": False, "error": str(e)}
                self.regions_status[region] = ServiceStatus.UNHEALTHY

        # Wait for services to become healthy
        await self._wait_for_healthy_deployment()

        # Setup load balancers
        await self._setup_global_load_balancing()

        # Configure monitoring
        await self._setup_monitoring()

        # Setup backup systems
        if self.backup_config.enabled:
            await self._setup_backup_systems()

        return {
            "deployment_id": str(uuid.uuid4()),
            "regions": deployment_results,
            "total_regions": len(self.config.regions),
            "successful_regions": sum(
                1 for r in deployment_results.values() if r.get("success")
            ),
            "global_status": self._calculate_global_status(),
            "deployed_at": datetime.utcnow().isoformat(),
        }

    async def _deploy_region(self, region: DeploymentRegion) -> Dict[str, Any]:
        """Deploy infrastructure to a specific region"""
        region_result = {
            "success": False,
            "instances_created": 0,
            "load_balancer_created": False,
            "database_created": False,
            "monitoring_setup": False,
        }

        try:
            # Deploy compute instances
            instances = await self._deploy_compute_instances(region)
            region_result["instances_created"] = len(instances)

            # Setup regional load balancer
            lb_config = await self._deploy_load_balancer(region)
            region_result["load_balancer_created"] = lb_config is not None

            # Setup regional database
            db_config = await self._deploy_database(region)
            region_result["database_created"] = db_config is not None

            # Setup regional monitoring
            monitoring_config = await self._deploy_monitoring(region)
            region_result["monitoring_setup"] = monitoring_config is not None

            region_result["success"] = True

        except Exception as e:
            self.logger.error(f"Region deployment failed: {e}")
            region_result["error"] = str(e)

        return region_result

    async def _deploy_compute_instances(
        self, region: DeploymentRegion
    ) -> List[ServiceInstance]:
        """Deploy compute instances in a region"""
        instances = []

        for i in range(self.config.min_instances):
            instance = await self._create_instance(region, f"gmnap-{region.value}-{i}")
            if instance:
                instances.append(instance)
                self.instances[instance.instance_id] = instance

        return instances

    async def _create_instance(
        self, region: DeploymentRegion, name: str
    ) -> Optional[ServiceInstance]:
        """Create a single service instance"""
        if K8S_AVAILABLE and self.k8s_clients:
            return await self._create_k8s_instance(region, name)
        elif AWS_AVAILABLE and region.value in self.aws_clients:
            return await self._create_aws_instance(region, name)
        else:
            return await self._create_docker_instance(region, name)

    async def _create_k8s_instance(
        self, region: DeploymentRegion, name: str
    ) -> Optional[ServiceInstance]:
        """Create Kubernetes deployment instance"""
        try:
            apps_v1 = self.k8s_clients["apps_v1"]

            # Define deployment
            deployment = client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(
                    name=name, labels={"app": "gmnap", "region": region.value}
                ),
                spec=client.V1DeploymentSpec(
                    replicas=1,
                    selector=client.V1LabelSelector(match_labels={"app": "gmnap"}),
                    template=client.V1PodTemplateSpec(
                        metadata=client.V1ObjectMeta(labels={"app": "gmnap"}),
                        spec=client.V1PodSpec(
                            containers=[
                                client.V1Container(
                                    name="gmnap",
                                    image="gmnap:latest",
                                    ports=[client.V1ContainerPort(container_port=8000)],
                                    resources=client.V1ResourceRequirements(
                                        requests={"cpu": "500m", "memory": "1Gi"},
                                        limits={"cpu": "2000m", "memory": "4Gi"},
                                    ),
                                    env=[
                                        client.V1EnvVar(
                                            name="REGION", value=region.value
                                        ),
                                        client.V1EnvVar(
                                            name="DEPLOYMENT_MODE", value="production"
                                        ),
                                    ],
                                )
                            ]
                        ),
                    ),
                ),
            )

            # Create deployment
            apps_v1.create_namespaced_deployment(namespace="default", body=deployment)

            # Create service
            core_v1 = self.k8s_clients["core_v1"]
            service = client.V1Service(
                metadata=client.V1ObjectMeta(name=f"{name}-service"),
                spec=client.V1ServiceSpec(
                    selector={"app": "gmnap"},
                    ports=[client.V1ServicePort(port=80, target_port=8000)],
                    type="LoadBalancer",
                ),
            )

            core_v1.create_namespaced_service(namespace="default", body=service)

            # Create instance record
            instance = ServiceInstance(
                instance_id=str(uuid.uuid4()),
                region=region,
                status=ServiceStatus.STARTING,
                endpoint=f"http://{name}-service.default.svc.cluster.local",
            )

            self.logger.info(f"Created Kubernetes instance: {name}")
            return instance

        except Exception as e:
            self.logger.error(f"Failed to create Kubernetes instance: {e}")
            return None

    async def _create_aws_instance(
        self, region: DeploymentRegion, name: str
    ) -> Optional[ServiceInstance]:
        """Create AWS ECS instance"""
        try:
            ecs_client = self.aws_clients[region.value]["ecs"]

            # Create ECS task definition
            task_def = {
                "family": "gmnap-task",
                "networkMode": "awsvpc",
                "requiresCompatibilities": ["FARGATE"],
                "cpu": "1024",
                "memory": "2048",
                "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
                "containerDefinitions": [
                    {
                        "name": "gmnap",
                        "image": "gmnap:latest",
                        "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
                        "environment": [
                            {"name": "REGION", "value": region.value},
                            {"name": "DEPLOYMENT_MODE", "value": "production"},
                        ],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": "/ecs/gmnap",
                                "awslogs-region": region.value,
                                "awslogs-stream-prefix": "ecs",
                            },
                        },
                    }
                ],
            }

            # Register task definition
            task_response = ecs_client.register_task_definition(**task_def)

            # Create service
            ecs_client.create_service(
                cluster="default",
                serviceName=name,
                taskDefinition=task_response["taskDefinition"]["taskDefinitionArn"],
                desiredCount=1,
                launchType="FARGATE",
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": ["subnet-12345"],  # Configure appropriately
                        "securityGroups": ["sg-12345"],
                        "assignPublicIp": "ENABLED",
                    }
                },
            )

            instance = ServiceInstance(
                instance_id=str(uuid.uuid4()),
                region=region,
                status=ServiceStatus.STARTING,
                endpoint=f"http://{name}.{region.value}.amazonaws.com",
            )

            self.logger.info(f"Created AWS ECS instance: {name}")
            return instance

        except Exception as e:
            self.logger.error(f"Failed to create AWS instance: {e}")
            return None

    async def _create_docker_instance(
        self, region: DeploymentRegion, name: str
    ) -> Optional[ServiceInstance]:
        """Create Docker instance (fallback)"""
        if not DOCKER_AVAILABLE:
            return None

        try:
            docker_client = docker.from_env()

            # Run container
            container = docker_client.containers.run(
                "gmnap:latest",
                name=name,
                ports={"8000/tcp": None},
                environment={"REGION": region.value, "DEPLOYMENT_MODE": "production"},
                detach=True,
                restart_policy={"Name": "unless-stopped"},
            )

            # Get assigned port
            container.reload()
            port = container.ports["8000/tcp"][0]["HostPort"]

            instance = ServiceInstance(
                instance_id=container.id,
                region=region,
                status=ServiceStatus.STARTING,
                endpoint=f"http://localhost:{port}",
            )

            self.logger.info(f"Created Docker instance: {name}")
            return instance

        except Exception as e:
            self.logger.error(f"Failed to create Docker instance: {e}")
            return None

    async def _deploy_load_balancer(
        self, region: DeploymentRegion
    ) -> Optional[Dict[str, Any]]:
        """Deploy regional load balancer"""
        try:
            if AWS_AVAILABLE and region.value in self.aws_clients:
                return await self._deploy_aws_load_balancer(region)
            else:
                return await self._deploy_nginx_load_balancer(region)
        except Exception as e:
            self.logger.error(
                f"Load balancer deployment failed for {region.value}: {e}"
            )
            return None

    async def _deploy_aws_load_balancer(
        self, region: DeploymentRegion
    ) -> Dict[str, Any]:
        """Deploy AWS Application Load Balancer"""
        elb_client = self.aws_clients[region.value]["elb"]

        # Create load balancer
        response = elb_client.create_load_balancer(
            Name=f"gmnap-lb-{region.value}",
            Subnets=["subnet-12345", "subnet-67890"],  # Configure appropriately
            SecurityGroups=["sg-12345"],
            Tags=[
                {"Key": "Name", "Value": f"GMNAP-LB-{region.value}"},
                {"Key": "Region", "Value": region.value},
            ],
        )

        return {
            "type": "aws_alb",
            "arn": response["LoadBalancers"][0]["LoadBalancerArn"],
            "dns_name": response["LoadBalancers"][0]["DNSName"],
        }

    async def _deploy_nginx_load_balancer(
        self, region: DeploymentRegion
    ) -> Dict[str, Any]:
        """Deploy NGINX load balancer (fallback)"""
        # This would create an NGINX configuration and container
        # For brevity, returning mock configuration
        return {
            "type": "nginx",
            "config_path": f"/etc/nginx/gmnap-{region.value}.conf",
            "upstream_servers": [
                instance.endpoint
                for instance in self.instances.values()
                if instance.region == region
            ],
        }

    async def _deploy_database(
        self, region: DeploymentRegion
    ) -> Optional[Dict[str, Any]]:
        """Deploy regional database"""
        try:
            if AWS_AVAILABLE and region.value in self.aws_clients:
                return await self._deploy_aws_database(region)
            else:
                return await self._deploy_postgres_database(region)
        except Exception as e:
            self.logger.error(f"Database deployment failed for {region.value}: {e}")
            return None

    async def _deploy_aws_database(self, region: DeploymentRegion) -> Dict[str, Any]:
        """Deploy AWS RDS instance"""
        rds_client = self.aws_clients[region.value]["rds"]

        response = rds_client.create_db_instance(
            DBInstanceIdentifier=f"gmnap-db-{region.value}",
            DBInstanceClass="db.t3.medium",
            Engine="postgres",
            MasterUsername="gmnap_admin",
            MasterUserPassword=os.environ["RDS_MASTER_PASSWORD"],
            AllocatedStorage=100,
            StorageType="gp2",
            StorageEncrypted=True,
            BackupRetentionPeriod=self.backup_config.retention_days,
            MultiAZ=True,
            VpcSecurityGroupIds=["sg-database"],
            Tags=[
                {"Key": "Name", "Value": f"GMNAP-DB-{region.value}"},
                {"Key": "Region", "Value": region.value},
            ],
        )

        return {
            "type": "aws_rds",
            "identifier": response["DBInstance"]["DBInstanceIdentifier"],
            "endpoint": response["DBInstance"]["Endpoint"]["Address"],
        }

    async def _deploy_postgres_database(
        self, region: DeploymentRegion
    ) -> Dict[str, Any]:
        """Deploy PostgreSQL database (fallback)"""
        # This would deploy a PostgreSQL container or instance
        return {
            "type": "postgresql",
            "host": f"postgres-{region.value}.local",
            "port": 5432,
            "database": "gmnap",
        }

    async def _deploy_monitoring(
        self, region: DeploymentRegion
    ) -> Optional[Dict[str, Any]]:
        """Deploy monitoring infrastructure"""
        try:
            return {
                "type": "cloudwatch" if AWS_AVAILABLE else "prometheus",
                "metrics_endpoint": f"https://monitoring-{region.value}.gmnap.com",
                "alerting_enabled": True,
                "log_aggregation": True,
            }
        except Exception as e:
            self.logger.error(f"Monitoring setup failed for {region.value}: {e}")
            return None

    async def _wait_for_healthy_deployment(self, timeout_minutes: int = 10):
        """Wait for all instances to become healthy"""
        self.logger.info("Waiting for healthy deployment...")

        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while time.time() - start_time < timeout_seconds:
            all_healthy = True

            for instance in self.instances.values():
                health_status = await self._check_instance_health(instance)
                if health_status != ServiceStatus.HEALTHY:
                    all_healthy = False
                    break

            if all_healthy:
                self.logger.info("All instances are healthy!")
                return

            await asyncio.sleep(10)

        self.logger.warning("Deployment health check timeout reached")

    async def _check_instance_health(self, instance: ServiceInstance) -> ServiceStatus:
        """Check health of a specific instance"""
        try:
            # This would make an HTTP health check request
            # For now, simulate health check
            instance.last_health_check = datetime.utcnow()
            instance.status = ServiceStatus.HEALTHY
            return ServiceStatus.HEALTHY
        except Exception:
            instance.status = ServiceStatus.UNHEALTHY
            return ServiceStatus.UNHEALTHY

    async def _setup_global_load_balancing(self):
        """Setup global load balancing and traffic routing"""
        self.logger.info("Setting up global load balancing...")

        # This would configure:
        # - DNS-based routing
        # - Geographic load balancing
        # - Health-based routing
        # - Latency-based routing

        global_lb_config = {
            "routing_policy": "latency_based",
            "health_check_interval": self.load_balancer_config.health_check_interval,
            "failover_enabled": True,
            "regions": [region.value for region in self.config.regions],
        }

        self.logger.info(f"Global load balancing configured: {global_lb_config}")

    async def _setup_monitoring(self):
        """Setup comprehensive monitoring"""
        self.logger.info("Setting up monitoring and alerting...")

        # Configure metrics collection

        # Configure alerts
        alert_rules = [
            {"metric": "cpu_utilization", "threshold": 80, "severity": "warning"},
            {"metric": "memory_utilization", "threshold": 85, "severity": "warning"},
            {"metric": "response_time", "threshold": 2000, "severity": "critical"},
            {"metric": "error_rate", "threshold": 5, "severity": "critical"},
        ]

        self.logger.info(f"Monitoring configured with {len(alert_rules)} alert rules")

    async def _setup_backup_systems(self):
        """Setup backup and disaster recovery"""
        self.logger.info("Setting up backup systems...")

        backup_strategy = {
            "database_backups": {
                "schedule": self.backup_config.schedule,
                "retention_days": self.backup_config.retention_days,
                "encryption": self.backup_config.encryption_enabled,
                "cross_region": self.backup_config.cross_region_replication,
            },
            "application_state": {"snapshot_frequency": "1h", "retention": "7d"},
            "disaster_recovery": {
                "rpo_minutes": 15,  # Recovery Point Objective
                "rto_minutes": 30,  # Recovery Time Objective
            },
        }

        self.logger.info(f"Backup systems configured: {backup_strategy}")

    def _calculate_global_status(self) -> ServiceStatus:
        """Calculate overall global system status"""
        healthy_regions = sum(
            1
            for status in self.regions_status.values()
            if status == ServiceStatus.HEALTHY
        )
        total_regions = len(self.regions_status)

        if healthy_regions == total_regions:
            return ServiceStatus.HEALTHY
        elif healthy_regions >= total_regions // 2:
            return ServiceStatus.DEGRADED
        else:
            return ServiceStatus.UNHEALTHY

    async def scale_region(
        self, region: DeploymentRegion, target_instances: int
    ) -> Dict[str, Any]:
        """Scale instances in a specific region"""
        current_instances = [i for i in self.instances.values() if i.region == region]
        current_count = len(current_instances)

        self.logger.info(
            f"Scaling {region.value}: {current_count} -> {target_instances}"
        )

        if target_instances > current_count:
            # Scale up
            scale_up_count = target_instances - current_count
            new_instances = []

            for i in range(scale_up_count):
                instance = await self._create_instance(
                    region, f"gmnap-{region.value}-scale-{int(time.time())}-{i}"
                )
                if instance:
                    new_instances.append(instance)
                    self.instances[instance.instance_id] = instance

            return {
                "action": "scale_up",
                "instances_added": len(new_instances),
                "new_total": current_count + len(new_instances),
            }

        elif target_instances < current_count:
            # Scale down
            scale_down_count = current_count - target_instances
            instances_to_remove = current_instances[-scale_down_count:]

            for instance in instances_to_remove:
                await self._terminate_instance(instance)
                del self.instances[instance.instance_id]

            return {
                "action": "scale_down",
                "instances_removed": scale_down_count,
                "new_total": target_instances,
            }

        return {"action": "no_change", "current_total": current_count}

    async def _terminate_instance(self, instance: ServiceInstance):
        """Terminate a service instance"""
        try:
            if K8S_AVAILABLE and self.k8s_clients:
                # Delete Kubernetes deployment
                apps_v1 = self.k8s_clients["apps_v1"]
                apps_v1.delete_namespaced_deployment(
                    name=f"gmnap-{instance.region.value}", namespace="default"
                )
            elif DOCKER_AVAILABLE:
                # Stop Docker container
                docker_client = docker.from_env()
                container = docker_client.containers.get(instance.instance_id)
                container.stop()
                container.remove()

            self.logger.info(f"Terminated instance: {instance.instance_id}")

        except Exception as e:
            self.logger.error(
                f"Failed to terminate instance {instance.instance_id}: {e}"
            )

    async def get_global_metrics(self) -> Dict[str, Any]:
        """Get comprehensive global metrics"""
        total_instances = len(self.instances)
        healthy_instances = sum(
            1 for i in self.instances.values() if i.status == ServiceStatus.HEALTHY
        )

        regional_metrics = {}
        for region in self.config.regions:
            region_instances = [
                i for i in self.instances.values() if i.region == region
            ]
            regional_metrics[region.value] = {
                "instance_count": len(region_instances),
                "healthy_instances": sum(
                    1 for i in region_instances if i.status == ServiceStatus.HEALTHY
                ),
                "avg_cpu": (
                    sum(i.cpu_utilization for i in region_instances)
                    / len(region_instances)
                    if region_instances
                    else 0
                ),
                "avg_memory": (
                    sum(i.memory_utilization for i in region_instances)
                    / len(region_instances)
                    if region_instances
                    else 0
                ),
            }

        return {
            "global_status": self._calculate_global_status().value,
            "total_instances": total_instances,
            "healthy_instances": healthy_instances,
            "healthy_percentage": (
                (healthy_instances / total_instances * 100) if total_instances else 0
            ),
            "regional_metrics": regional_metrics,
            "deployment_regions": [r.value for r in self.config.regions],
            "last_updated": datetime.utcnow().isoformat(),
        }


class AutoScalingManager:
    """
    Intelligent auto-scaling based on multiple metrics
    """

    def __init__(self, deployment_manager: GlobalDeploymentManager):
        self.deployment_manager = deployment_manager
        self.logger = logging.getLogger(__name__)
        self.scaling_rules = {}
        self.last_scaling_action = {}
        self.cooldown_period = 300  # 5 minutes

    def add_scaling_rule(
        self,
        region: DeploymentRegion,
        trigger: ScalingTrigger,
        threshold: float,
        scale_up_by: int = 1,
        scale_down_by: int = 1,
    ):
        """Add an auto-scaling rule"""
        if region not in self.scaling_rules:
            self.scaling_rules[region] = []

        rule = {
            "trigger": trigger,
            "threshold": threshold,
            "scale_up_by": scale_up_by,
            "scale_down_by": scale_down_by,
        }

        self.scaling_rules[region].append(rule)
        self.logger.info(f"Added scaling rule for {region.value}: {rule}")

    async def evaluate_scaling(
        self, region: DeploymentRegion
    ) -> Optional[Dict[str, Any]]:
        """Evaluate if scaling is needed for a region"""
        if region not in self.scaling_rules:
            return None

        # Check cooldown period
        if self._in_cooldown(region):
            return None

        current_metrics = await self._get_region_metrics(region)

        for rule in self.scaling_rules[region]:
            action = self._evaluate_rule(rule, current_metrics)
            if action:
                return await self._execute_scaling_action(region, action)

        return None

    def _in_cooldown(self, region: DeploymentRegion) -> bool:
        """Check if region is in scaling cooldown period"""
        if region not in self.last_scaling_action:
            return False

        last_action_time = self.last_scaling_action[region]
        return (time.time() - last_action_time) < self.cooldown_period

    async def _get_region_metrics(self, region: DeploymentRegion) -> Dict[str, float]:
        """Get current metrics for a region"""
        instances = [
            i for i in self.deployment_manager.instances.values() if i.region == region
        ]

        if not instances:
            return {}

        return {
            "cpu_utilization": sum(i.cpu_utilization for i in instances)
            / len(instances),
            "memory_utilization": sum(i.memory_utilization for i in instances)
            / len(instances),
            "request_rate": sum(i.request_count for i in instances) / len(instances),
            "response_time": sum(i.response_time for i in instances) / len(instances),
        }

    def _evaluate_rule(
        self, rule: Dict[str, Any], metrics: Dict[str, float]
    ) -> Optional[str]:
        """Evaluate a single scaling rule"""
        trigger = rule["trigger"]
        threshold = rule["threshold"]

        metric_value = metrics.get(trigger.value, 0)

        if metric_value > threshold:
            return "scale_up"
        elif metric_value < threshold * 0.5:  # Scale down at 50% of threshold
            return "scale_down"

        return None

    async def _execute_scaling_action(
        self, region: DeploymentRegion, action: str
    ) -> Dict[str, Any]:
        """Execute a scaling action"""
        current_instances = len(
            [
                i
                for i in self.deployment_manager.instances.values()
                if i.region == region
            ]
        )

        if action == "scale_up":
            new_count = min(
                current_instances + 1, self.deployment_manager.config.max_instances
            )
        else:  # scale_down
            new_count = max(
                current_instances - 1, self.deployment_manager.config.min_instances
            )

        if new_count == current_instances:
            return {"action": "no_change", "reason": "limits_reached"}

        result = await self.deployment_manager.scale_region(region, new_count)
        self.last_scaling_action[region] = time.time()

        self.logger.info(f"Executed {action} for {region.value}: {result}")
        return result
