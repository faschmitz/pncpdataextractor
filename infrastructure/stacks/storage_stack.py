"""
Storage Stack para PNCP Data Extractor

Esta stack define todos os recursos de armazenamento:
- Bucket S3 para dados brutos (raw data)
- Bucket S3 para dados consolidados
- Políticas de lifecycle
- Configurações de versionamento e criptografia
"""

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from constructs import Construct

class StorageStack(Stack):
    """Stack para recursos de armazenamento S3"""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        app_name: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.app_name = app_name
        self.env_name = environment
        
        # Criar buckets S3
        self._create_data_bucket()
        self._create_outputs()
    
    def _create_data_bucket(self):
        """Cria o bucket principal para dados PNCP"""
        
        # Configurações de lifecycle para otimização de custos
        lifecycle_rules = [
            s3.LifecycleRule(
                id="DataOptimization",
                enabled=True,
                # Dados recentes (30 dias): Standard
                transitions=[
                    s3.Transition(
                        storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                        transition_after=Duration.days(30)
                    ),
                    s3.Transition(
                        storage_class=s3.StorageClass.GLACIER,
                        transition_after=Duration.days(90)
                    ),
                    s3.Transition(
                        storage_class=s3.StorageClass.DEEP_ARCHIVE,
                        transition_after=Duration.days(365)
                    )
                ]
            ),
            s3.LifecycleRule(
                id="LogsCleanup",
                enabled=True,
                prefix="logs/",
                expiration=Duration.days(90)  # Logs são removidos após 90 dias
            ),
            s3.LifecycleRule(
                id="IncompleteMultipartUploads",
                enabled=True,
                abort_incomplete_multipart_upload_after=Duration.days(7)
            )
        ]
        
        # Bucket principal para dados
        self.data_bucket = s3.Bucket(
            self,
            "DataBucket",
            bucket_name=f"{self.app_name}-data-{self.env_name}",
            # Segurança
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            
            # Versionamento para recuperação
            versioned=True,
            
            # Lifecycle rules para otimização de custos
            lifecycle_rules=lifecycle_rules,
            
            # CORS para acesso externo controlado
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.HEAD],
                    allowed_origins=["*"],  # Configurar domínios específicos em produção
                    allowed_headers=["*"],
                    max_age=3600
                )
            ],
            
            # Notificações de eventos (para processamento futuro)
            event_bridge_enabled=True,
            
            # Política de remoção
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False  # Proteger dados em produção
        )
        
        # Configurar notificações do bucket para monitoramento
        # Será usado pelo monitoring stack para alertas
        
        # Bucket para logs de acesso (opcional, para auditoria)
        self.access_logs_bucket = s3.Bucket(
            self,
            "AccessLogsBucket",
            bucket_name=f"{self.app_name}-access-logs-{self.env_name}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="AccessLogsCleanup",
                    enabled=True,
                    expiration=Duration.days(30)  # Logs de acesso mantidos por 30 dias
                )
            ],
            removal_policy=RemovalPolicy.DESTROY  # Logs podem ser removidos
        )
        
        # Configurar logging de acesso no bucket principal
    
    def _create_outputs(self):
        """Criar outputs para outras stacks"""
        
        # Nome do bucket principal (usado por outras stacks)
        CfnOutput(
            self,
            "DataBucketName",
            value=self.data_bucket.bucket_name,
            description="Nome do bucket S3 para dados PNCP",
            export_name=f"{self.stack_name}-DataBucketName"
        )
        
        # ARN do bucket principal
        CfnOutput(
            self,
            "DataBucketArn",
            value=self.data_bucket.bucket_arn,
            description="ARN do bucket S3 para dados PNCP",
            export_name=f"{self.stack_name}-DataBucketArn"
        )
        
        # URL do bucket para acessos diretos
        CfnOutput(
            self,
            "DataBucketUrl",
            value=f"s3://{self.data_bucket.bucket_name}",
            description="URL S3 do bucket de dados",
            export_name=f"{self.stack_name}-DataBucketUrl"
        )
        
        # Nome do bucket de logs
        CfnOutput(
            self,
            "AccessLogsBucketName",
            value=self.access_logs_bucket.bucket_name,
            description="Nome do bucket de logs de acesso",
            export_name=f"{self.stack_name}-AccessLogsBucketName"
        )