"""
Compute Stack para PNCP Data Extractor

Esta stack define todos os recursos de computação:
- ECS Cluster com Fargate
- Task Definition para o extractor
- ECR repository para container images
- VPC e networking (se necessário)
- Auto Scaling configurações
"""

from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_logs as logs,
    aws_iam as iam,
    Duration,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .storage_stack import StorageStack
    from .security_stack import SecurityStack

class ComputeStack(Stack):
    """Stack para recursos de computação ECS"""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        storage_stack: "StorageStack",
        security_stack: "SecurityStack",
        app_name: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.storage_stack = storage_stack
        self.security_stack = security_stack
        self.app_name = app_name
        self.env_name = environment
        
        # Criar recursos de computação
        self._create_vpc()
        self._create_ecr_repository()
        self._create_ecs_cluster()
        self._create_task_definition()
        self._create_outputs()
    
    def _create_vpc(self):
        """Criar VPC para recursos ECS (opcional - pode usar VPC default)"""
        
        # Para produção, recomenda-se VPC dedicada
        # Para simplicidade inicial, pode usar VPC default
        
        # Opção 1: VPC dedicada (produção)
        self.vpc = ec2.Vpc(
            self,
            "VPC",
            vpc_name=f"{self.app_name}-vpc-{self.env_name}",
            max_azs=2,  # Multi-AZ para alta disponibilidade
            nat_gateways=1,  # 1 NAT Gateway para reduzir custos
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True
        )
        
        # VPC Endpoints para reduzir custos de NAT Gateway
        # Endpoint para S3
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)]
        )
        
        # Endpoint para ECR (pull de images)
        self.vpc.add_interface_endpoint(
            "ECREndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        )
        
        # Endpoint para ECR Docker
        self.vpc.add_interface_endpoint(
            "ECRDockerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        )
        
        # Endpoint para Secrets Manager
        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        )
        
        # Security Group para ECS tasks
        self.ecs_security_group = ec2.SecurityGroup(
            self,
            "ECSSecurityGroup",
            vpc=self.vpc,
            description="Security group para ECS tasks do PNCP Extractor",
            allow_all_outbound=True  # Necessário para API calls
        )
        
        # Regra de ingress não necessária para batch processing
        # Tasks apenas fazem requests outbound
    
    def _create_ecr_repository(self):
        """Criar repository ECR para container images"""
        
        self.ecr_repository = ecr.Repository(
            self,
            "ECRRepository",
            repository_name=f"{self.app_name}-{self.env_name}",
            image_scan_on_push=True,  # Scanning de segurança
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Manter apenas as 10 imagens mais recentes",
                    max_image_count=10
                ),
                ecr.LifecycleRule(
                    description="Remover imagens não taggeadas após 1 dia",
                    max_image_age=Duration.days(1),
                    rule_priority=1,
                    tag_status=ecr.TagStatus.UNTAGGED
                )
            ],
            removal_policy=RemovalPolicy.DESTROY  # Para desenvolvimento
        )
        
        # Política de acesso para GitHub Actions (CI/CD)
        self.ecr_repository.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("ecs-tasks.amazonaws.com")],
                actions=[
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage"
                ]
            )
        )
    
    def _create_ecs_cluster(self):
        """Criar ECS Cluster com Fargate"""
        
        self.ecs_cluster = ecs.Cluster(
            self,
            "ECSCluster",
            cluster_name=f"{self.app_name}-cluster-{self.env_name}",
            vpc=self.vpc,
            container_insights=True,  # Monitoramento detalhado
            enable_fargate_capacity_providers=True
        )
        
        # Configurar capacity providers para otimização de custos
        self.ecs_cluster.add_capacity_provider(
            capacity_provider="FARGATE_SPOT",
            enable_managed_scaling=True,
            auto_scaling_group_provider=None,
            enable_managed_termination_protection=False,
            machine_image_type=None,
            spot_instance_draining=None,
            task_drain_time=Duration.minutes(5)
        )
    
    def _create_task_definition(self):
        """Criar Task Definition para o PNCP Extractor"""
        
        # CloudWatch Log Group
        self.log_group = logs.LogGroup(
            self,
            "ECSLogGroup",
            log_group_name=f"/aws/ecs/{self.app_name}-{self.env_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Task Definition
        self.task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            family=f"{self.app_name}-task-{self.env_name}",
            cpu=1024,  # 1 vCPU - pode ser ajustado conforme necessidade
            memory_limit_mib=2048,  # 2GB RAM - pode ser ajustado
            execution_role=self.security_stack.ecs_execution_role,
            task_role=self.security_stack.ecs_task_role
        )
        
        # Container definition
        self.container = self.task_definition.add_container(
            "ExtractorContainer",
            image=ecs.ContainerImage.from_ecr_repository(
                repository=self.ecr_repository,
                tag="latest"
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="pncp-extractor",
                log_group=self.log_group
            ),
            environment={
                "AWS_DEFAULT_REGION": self.region,
                "S3_BUCKET": self.storage_stack.data_bucket.bucket_name,
                "ENVIRONMENT": self.env_name
            },
            secrets={
                # Secrets serão injetados automaticamente pelo aws_config.py
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(
                    self.security_stack.openai_secret,
                    field="api_key"
                )
            },
            # Health check
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "python -c 'import requests; import boto3; print(\"OK\")'"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60)
            ),
            # Resource limits
            memory_reservation_mib=1536,  # Soft limit
            stop_timeout=Duration.minutes(10)  # Tempo para graceful shutdown
        )
        
        # Task Definition para execução histórica (recursos maiores)
        self.historical_task_definition = ecs.FargateTaskDefinition(
            self,
            "HistoricalTaskDefinition",
            family=f"{self.app_name}-historical-task-{self.env_name}",
            cpu=2048,  # 2 vCPU para processamento pesado
            memory_limit_mib=4096,  # 4GB RAM
            execution_role=self.security_stack.ecs_execution_role,
            task_role=self.security_stack.ecs_task_role
        )
        
        self.historical_container = self.historical_task_definition.add_container(
            "HistoricalExtractorContainer",
            image=ecs.ContainerImage.from_ecr_repository(
                repository=self.ecr_repository,
                tag="latest"
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="pncp-extractor-historical",
                log_group=self.log_group
            ),
            environment={
                "AWS_DEFAULT_REGION": self.region,
                "S3_BUCKET": self.storage_stack.data_bucket.bucket_name,
                "ENVIRONMENT": self.env_name
            },
            secrets={
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(
                    self.security_stack.openai_secret,
                    field="api_key"
                )
            },
            # Comando para execução histórica
            command=["python", "extractor.py", "--historical"],
            memory_reservation_mib=3072,
            stop_timeout=Duration.minutes(15)
        )
    
    def _create_outputs(self):
        """Criar outputs para outras stacks"""
        
        # Cluster ARN
        CfnOutput(
            self,
            "ECSClusterArn",
            value=self.ecs_cluster.cluster_arn,
            description="ARN do ECS Cluster",
            export_name=f"{self.stack_name}-ECSClusterArn"
        )
        
        # Cluster Name
        CfnOutput(
            self,
            "ECSClusterName",
            value=self.ecs_cluster.cluster_name,
            description="Nome do ECS Cluster",
            export_name=f"{self.stack_name}-ECSClusterName"
        )
        
        # Task Definition ARNs
        CfnOutput(
            self,
            "TaskDefinitionArn",
            value=self.task_definition.task_definition_arn,
            description="ARN da Task Definition principal",
            export_name=f"{self.stack_name}-TaskDefinitionArn"
        )
        
        CfnOutput(
            self,
            "HistoricalTaskDefinitionArn",
            value=self.historical_task_definition.task_definition_arn,
            description="ARN da Task Definition para execução histórica",
            export_name=f"{self.stack_name}-HistoricalTaskDefinitionArn"
        )
        
        # ECR Repository
        CfnOutput(
            self,
            "ECRRepositoryUri",
            value=self.ecr_repository.repository_uri,
            description="URI do ECR Repository",
            export_name=f"{self.stack_name}-ECRRepositoryUri"
        )
        
        CfnOutput(
            self,
            "ECRRepositoryName",
            value=self.ecr_repository.repository_name,
            description="Nome do ECR Repository",
            export_name=f"{self.stack_name}-ECRRepositoryName"
        )
        
        # VPC ID (para outras stacks)
        CfnOutput(
            self,
            "VPCId",
            value=self.vpc.vpc_id,
            description="ID da VPC",
            export_name=f"{self.stack_name}-VPCId"
        )
        
        # Subnet IDs
        CfnOutput(
            self,
            "PrivateSubnetIds",
            value=",".join([subnet.subnet_id for subnet in self.vpc.private_subnets]),
            description="IDs das subnets privadas",
            export_name=f"{self.stack_name}-PrivateSubnetIds"
        )
        
        # Security Group ID
        CfnOutput(
            self,
            "ECSSecurityGroupId",
            value=self.ecs_security_group.security_group_id,
            description="ID do Security Group do ECS",
            export_name=f"{self.stack_name}-ECSSecurityGroupId"
        )