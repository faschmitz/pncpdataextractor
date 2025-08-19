"""
Security Stack para PNCP Data Extractor

Esta stack define todos os recursos de segurança:
- IAM roles para ECS tasks
- Políticas de acesso ao S3
- Secrets Manager para API keys
- Políticas de least privilege
"""

from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_kms as kms,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .storage_stack import StorageStack

class SecurityStack(Stack):
    """Stack para recursos de segurança"""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        storage_stack: "StorageStack",
        app_name: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.storage_stack = storage_stack
        self.app_name = app_name
        self.env_name = environment
        
        # Criar recursos de segurança
        self._create_kms_key()
        self._create_secrets()
        self._create_iam_roles()
        self._create_outputs()
    
    def _create_kms_key(self):
        """Criar chave KMS para criptografia de secrets"""
        self.kms_key = kms.Key(
            self,
            "SecretsKMSKey",
            description=f"KMS key para secrets do {self.app_name}",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Alias para facilitar identificação
        kms.Alias(
            self,
            "SecretsKMSKeyAlias",
            alias_name=f"alias/{self.app_name}-secrets-{self.env_name}",
            target_key=self.kms_key
        )
    
    def _create_secrets(self):
        """Criar secrets no Secrets Manager"""
        
        # Secret para OpenAI API Key
        self.openai_secret = secretsmanager.Secret(
            self,
            "OpenAIAPIKeySecret",
            secret_name=f"{self.app_name}/openai-api-key",
            description="OpenAI API key para filtro LLM do PNCP Extractor",
            encryption_key=self.kms_key,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"api_key": ""}',
                generate_string_key="api_key",
                exclude_characters='"@/\\'
            ),
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Secret para configurações adicionais (se necessário)
        self.app_config_secret = secretsmanager.Secret(
            self,
            "AppConfigSecret",
            secret_name=f"{self.app_name}/app-config",
            description="Configurações sensíveis da aplicação PNCP Extractor",
            encryption_key=self.kms_key,
            secret_string_value=secretsmanager.SecretStringGenerator(
                secret_string_template='{}',
                generate_string_key="config"
            ),
            removal_policy=RemovalPolicy.RETAIN
        )
    
    def _create_iam_roles(self):
        """Criar IAM roles e políticas"""
        
        # Role de execução para ECS tasks
        self.ecs_execution_role = iam.Role(
            self,
            "ECSExecutionRole",
            role_name=f"{self.app_name}-ecs-execution-{self.env_name}",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role para execução de tasks ECS do PNCP Extractor"
        )
        
        # Adicionar políticas gerenciadas necessárias
        self.ecs_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
        )
        
        # Política customizada para acessar secrets
        secrets_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            resources=[
                self.openai_secret.secret_arn,
                self.app_config_secret.secret_arn
            ]
        )
        
        # Política para descriptografar com KMS
        kms_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "kms:Decrypt",
                "kms:DescribeKey"
            ],
            resources=[self.kms_key.key_arn]
        )
        
        self.ecs_execution_role.add_to_policy(secrets_policy)
        self.ecs_execution_role.add_to_policy(kms_policy)
        
        # Role da task (runtime role)
        self.ecs_task_role = iam.Role(
            self,
            "ECSTaskRole",
            role_name=f"{self.app_name}-ecs-task-{self.env_name}",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role de runtime para tasks ECS do PNCP Extractor"
        )
        
        # Políticas para acessar S3
        s3_read_write_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:GetObjectVersion",
                "s3:PutObjectAcl"
            ],
            resources=[
                f"{self.storage_stack.data_bucket.bucket_arn}/*"
            ]
        )
        
        s3_list_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:GetBucketVersioning"
            ],
            resources=[
                self.storage_stack.data_bucket.bucket_arn
            ]
        )
        
        # Política para acessar secrets durante runtime
        runtime_secrets_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "secretsmanager:GetSecretValue"
            ],
            resources=[
                self.openai_secret.secret_arn,
                self.app_config_secret.secret_arn
            ]
        )
        
        self.ecs_task_role.add_to_policy(s3_read_write_policy)
        self.ecs_task_role.add_to_policy(s3_list_policy)
        self.ecs_task_role.add_to_policy(runtime_secrets_policy)
        self.ecs_task_role.add_to_policy(kms_policy)
        
        # Role para Step Functions
        self.step_functions_role = iam.Role(
            self,
            "StepFunctionsRole",
            role_name=f"{self.app_name}-stepfunctions-{self.env_name}",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            description="Role para Step Functions do PNCP Extractor"
        )
        
        # Política para executar ECS tasks
        ecs_run_task_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ecs:RunTask",
                "ecs:StopTask",
                "ecs:DescribeTasks"
            ],
            resources=["*"],  # Será refinado na compute stack
            conditions={
                "ArnLike": {
                    "ecs:cluster": f"arn:aws:ecs:{self.region}:{self.account}:cluster/{self.app_name}-*"
                }
            }
        )
        
        # Política para passar roles para ECS
        pass_role_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["iam:PassRole"],
            resources=[
                self.ecs_execution_role.role_arn,
                self.ecs_task_role.role_arn
            ]
        )
        
        # Política para SNS (notificações)
        sns_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "sns:Publish"
            ],
            resources=[f"arn:aws:sns:{self.region}:{self.account}:{self.app_name}-*"]
        )
        
        self.step_functions_role.add_to_policy(ecs_run_task_policy)
        self.step_functions_role.add_to_policy(pass_role_policy)
        self.step_functions_role.add_to_policy(sns_policy)
        
        # Role para EventBridge Scheduler
        self.scheduler_role = iam.Role(
            self,
            "SchedulerRole",
            role_name=f"{self.app_name}-scheduler-{self.env_name}",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
            description="Role para EventBridge Scheduler do PNCP Extractor"
        )
        
        # Política para invocar Step Functions
        invoke_stepfunctions_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "states:StartExecution"
            ],
            resources=[f"arn:aws:states:{self.region}:{self.account}:stateMachine:{self.app_name}-*"]
        )
        
        self.scheduler_role.add_to_policy(invoke_stepfunctions_policy)
        
        # Role para acesso externo aos dados (sistemas consulta)
        self.external_access_role = iam.Role(
            self,
            "ExternalAccessRole",
            role_name=f"{self.app_name}-external-access-{self.env_name}",
            assumed_by=iam.AccountRootPrincipal(),  # Pode ser refinado para contas específicas
            description="Role para acesso externo aos dados do PNCP Extractor"
        )
        
        # Política de leitura apenas para dados
        external_read_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:ListBucket"
            ],
            resources=[
                self.storage_stack.data_bucket.bucket_arn,
                f"{self.storage_stack.data_bucket.bucket_arn}/raw-data/*",
                f"{self.storage_stack.data_bucket.bucket_arn}/consolidated/*"
            ]
        )
        
        self.external_access_role.add_to_policy(external_read_policy)
    
    def _create_outputs(self):
        """Criar outputs para outras stacks"""
        
        # ARNs das roles
        CfnOutput(
            self,
            "ECSExecutionRoleArn",
            value=self.ecs_execution_role.role_arn,
            description="ARN da role de execução ECS",
            export_name=f"{self.stack_name}-ECSExecutionRoleArn"
        )
        
        CfnOutput(
            self,
            "ECSTaskRoleArn",
            value=self.ecs_task_role.role_arn,
            description="ARN da role de runtime ECS",
            export_name=f"{self.stack_name}-ECSTaskRoleArn"
        )
        
        CfnOutput(
            self,
            "StepFunctionsRoleArn",
            value=self.step_functions_role.role_arn,
            description="ARN da role do Step Functions",
            export_name=f"{self.stack_name}-StepFunctionsRoleArn"
        )
        
        CfnOutput(
            self,
            "SchedulerRoleArn",
            value=self.scheduler_role.role_arn,
            description="ARN da role do EventBridge Scheduler",
            export_name=f"{self.stack_name}-SchedulerRoleArn"
        )
        
        # ARNs dos secrets
        CfnOutput(
            self,
            "OpenAISecretArn",
            value=self.openai_secret.secret_arn,
            description="ARN do secret da OpenAI API key",
            export_name=f"{self.stack_name}-OpenAISecretArn"
        )
        
        CfnOutput(
            self,
            "AppConfigSecretArn",
            value=self.app_config_secret.secret_arn,
            description="ARN do secret de configuração da aplicação",
            export_name=f"{self.stack_name}-AppConfigSecretArn"
        )
        
        # Nome dos secrets (para referência na aplicação)
        CfnOutput(
            self,
            "OpenAISecretName",
            value=self.openai_secret.secret_name,
            description="Nome do secret da OpenAI API key",
            export_name=f"{self.stack_name}-OpenAISecretName"
        )
        
        # ARN da chave KMS
        CfnOutput(
            self,
            "KMSKeyArn",
            value=self.kms_key.key_arn,
            description="ARN da chave KMS para secrets",
            export_name=f"{self.stack_name}-KMSKeyArn"
        )