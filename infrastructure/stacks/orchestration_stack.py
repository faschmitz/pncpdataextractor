"""
Orchestration Stack para PNCP Data Extractor

Esta stack define recursos de orquestração:
- Step Functions State Machine para workflow
- EventBridge Scheduler para execução diária
- SNS topics para notificações
- Definição completa do workflow de extração
"""

from aws_cdk import (
    Stack,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_scheduler as scheduler,
    aws_sns as sns,
    aws_ecs as ecs,
    Duration,
    CfnOutput
)
from constructs import Construct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .compute_stack import ComputeStack
    from .security_stack import SecurityStack

class OrchestrationStack(Stack):
    """Stack para orquestração e agendamento"""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        compute_stack: "ComputeStack",
        security_stack: "SecurityStack",
        app_name: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.compute_stack = compute_stack
        self.security_stack = security_stack
        self.app_name = app_name
        self.env_name = environment
        
        # Criar recursos de orquestração
        self._create_sns_topics()
        self._create_step_functions()
        self._create_scheduler()
        self._create_outputs()
    
    def _create_sns_topics(self):
        """Criar tópicos SNS para notificações"""
        
        # Tópico para notificações de sucesso
        self.success_topic = sns.Topic(
            self,
            "SuccessTopic",
            topic_name=f"{self.app_name}-success-{self.env_name}",
            display_name=f"PNCP Extractor Success Notifications - {self.env_name}"
        )
        
        # Tópico para notificações de falha
        self.failure_topic = sns.Topic(
            self,
            "FailureTopic", 
            topic_name=f"{self.app_name}-failure-{self.env_name}",
            display_name=f"PNCP Extractor Failure Notifications - {self.env_name}"
        )
        
        # Tópico para alertas de monitoramento
        self.alerts_topic = sns.Topic(
            self,
            "AlertsTopic",
            topic_name=f"{self.app_name}-alerts-{self.env_name}",
            display_name=f"PNCP Extractor Monitoring Alerts - {self.env_name}"
        )
        
        # Subscrições de exemplo (podem ser configuradas manualmente)
        # self.success_topic.add_subscription(
        #     sns.EmailSubscription("admin@leonora.com.br")
        # )
    
    def _create_step_functions(self):
        """Criar State Machine do Step Functions"""
        
        # Task para execução diária do extractor
        daily_extraction_task = sfn_tasks.EcsRunTask(
            self,
            "DailyExtractionTask",
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            cluster=self.compute_stack.ecs_cluster,
            task_definition=self.compute_stack.task_definition,
            launch_target=sfn_tasks.EcsFargateLaunchTarget(
                platform_version=ecs.FargatePlatformVersion.LATEST
            ),
            container_overrides=[
                sfn_tasks.ContainerOverride(
                    container_definition=self.compute_stack.container,
                    command=["python", "extractor.py"]  # Execução incremental padrão
                )
            ],
            assign_public_ip=True,  # Necessário se usar subnets públicas
            security_groups=[self.compute_stack.ecs_security_group],
            subnets=ecs.SubnetSelection(
                subnet_type=ecs.SubnetType.PRIVATE_WITH_EGRESS
            ),
            result_path="$.ExtractionResult",
            timeout=Duration.hours(3),  # Timeout de 3 horas
            heartbeat=Duration.minutes(5)
        )
        
        # Task para execução histórica (opcional, sob demanda)
        historical_extraction_task = sfn_tasks.EcsRunTask(
            self,
            "HistoricalExtractionTask",
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            cluster=self.compute_stack.ecs_cluster,
            task_definition=self.compute_stack.historical_task_definition,
            launch_target=sfn_tasks.EcsFargateLaunchTarget(
                platform_version=ecs.FargatePlatformVersion.LATEST
            ),
            container_overrides=[
                sfn_tasks.ContainerOverride(
                    container_definition=self.compute_stack.historical_container,
                    command=["python", "extractor.py", "--historical"]
                )
            ],
            assign_public_ip=True,
            security_groups=[self.compute_stack.ecs_security_group],
            subnets=ecs.SubnetSelection(
                subnet_type=ecs.SubnetType.PRIVATE_WITH_EGRESS
            ),
            result_path="$.HistoricalResult",
            timeout=Duration.hours(8),  # Timeout maior para histórico
            heartbeat=Duration.minutes(5)
        )
        
        # Task para notificação de sucesso
        success_notification = sfn_tasks.SnsPublish(
            self,
            "SuccessNotification",
            topic=self.success_topic,
            subject="PNCP Extractor - Execução Concluída com Sucesso",
            message=sfn.TaskInput.from_json_path_at("$.NotificationMessage"),
            result_path="$.NotificationResult"
        )
        
        # Task para notificação de falha
        failure_notification = sfn_tasks.SnsPublish(
            self,
            "FailureNotification",
            topic=self.failure_topic,
            subject="PNCP Extractor - Falha na Execução",
            message=sfn.TaskInput.from_json_path_at("$.ErrorMessage"),
            result_path="$.NotificationResult"
        )
        
        # Estado de preparação da mensagem de sucesso
        prepare_success_message = sfn.Pass(
            self,
            "PrepareSuccessMessage",
            result={
                "NotificationMessage": sfn.TaskInput.from_format(
                    "Extração PNCP concluída com sucesso.\\n\\n"
                    "Timestamp: {}\\n"
                    "Ambiente: {}\\n"
                    "Detalhes: {}",
                    sfn.JsonPath.string_at("$$.State.EnteredTime"),
                    self.env_name,
                    sfn.JsonPath.string_at("$.ExtractionResult")
                ).value
            },
            result_path="$"
        )
        
        # Estado de preparação da mensagem de erro
        prepare_error_message = sfn.Pass(
            self,
            "PrepareErrorMessage",
            result={
                "ErrorMessage": sfn.TaskInput.from_format(
                    "Falha na execução do PNCP Extractor.\\n\\n"
                    "Timestamp: {}\\n"
                    "Ambiente: {}\\n"
                    "Erro: {}",
                    sfn.JsonPath.string_at("$$.State.EnteredTime"),
                    self.env_name,
                    sfn.JsonPath.string_at("$.Error")
                ).value
            },
            result_path="$"
        )
        
        # Choice state para decidir tipo de execução
        execution_choice = sfn.Choice(
            self,
            "ExecutionChoice",
            comment="Escolher entre execução diária ou histórica"
        )
        
        # Definir o workflow principal
        workflow_definition = (
            execution_choice
            .when(
                sfn.Condition.string_equals("$.ExecutionType", "historical"),
                historical_extraction_task
                .next(prepare_success_message)
                .next(success_notification)
            )
            .otherwise(
                daily_extraction_task
                .next(prepare_success_message)
                .next(success_notification)
            )
            .add_catch(
                handler=(
                    prepare_error_message
                    .next(failure_notification)
                ),
                errors=["States.ALL"],
                result_path="$.Error"
            )
        )
        
        # Criar State Machine
        self.state_machine = sfn.StateMachine(
            self,
            "PNCPExtractorStateMachine",
            state_machine_name=f"{self.app_name}-workflow-{self.env_name}",
            definition=workflow_definition,
            role=self.security_stack.step_functions_role,
            timeout=Duration.hours(4),
            comment="Workflow de extração de dados PNCP com filtro LLM"
        )
    
    def _create_scheduler(self):
        """Criar EventBridge Scheduler para execução diária"""
        
        # Schedule para execução diária às 6:00 UTC (3:00 AM Brasil)
        self.daily_schedule = scheduler.CfnSchedule(
            self,
            "DailySchedule",
            name=f"{self.app_name}-daily-{self.env_name}",
            description="Agendamento diário para extração PNCP",
            
            # Expressão cron: todos os dias às 6:00 UTC
            schedule_expression="cron(0 6 * * ? *)",
            schedule_expression_timezone="UTC",
            
            # Estado do schedule
            state="ENABLED",
            
            # Configuração flexível de tempo
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="FLEXIBLE",
                maximum_window_minutes=30  # Permite execução até 30min após horário
            ),
            
            # Target: Step Functions State Machine
            target=scheduler.CfnSchedule.TargetProperty(
                arn=self.state_machine.state_machine_arn,
                role_arn=self.security_stack.scheduler_role.role_arn,
                
                # Input para execução diária (não histórica)
                input='{"ExecutionType": "daily", "Timestamp": "<aws.scheduler.scheduled-time>"}',
                
                # Configurações de retry
                retry_policy=scheduler.CfnSchedule.RetryPolicyProperty(
                    maximum_retry_attempts=2
                ),
                
                # Dead letter queue (opcional)
                # dead_letter_config=scheduler.CfnSchedule.DeadLetterConfigProperty(
                #     arn=dead_letter_queue_arn
                # )
            ),
            
            # Configurações do grupo (opcional)
            group_name="default"
        )
        
        # Schedule para execução semanal de consolidação (opcional)
        self.weekly_consolidation_schedule = scheduler.CfnSchedule(
            self,
            "WeeklyConsolidationSchedule",
            name=f"{self.app_name}-weekly-consolidation-{self.env_name}",
            description="Agendamento semanal para consolidação de dados PNCP",
            
            # Todos os domingos às 2:00 UTC
            schedule_expression="cron(0 2 ? * SUN *)",
            schedule_expression_timezone="UTC",
            
            state="ENABLED",
            
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="FLEXIBLE",
                maximum_window_minutes=60
            ),
            
            target=scheduler.CfnSchedule.TargetProperty(
                arn=self.state_machine.state_machine_arn,
                role_arn=self.security_stack.scheduler_role.role_arn,
                input='{"ExecutionType": "consolidation", "Timestamp": "<aws.scheduler.scheduled-time>"}',
                retry_policy=scheduler.CfnSchedule.RetryPolicyProperty(
                    maximum_retry_attempts=1
                )
            ),
            
            group_name="default"
        )
    
    def _create_outputs(self):
        """Criar outputs para outras stacks"""
        
        # State Machine ARN
        CfnOutput(
            self,
            "StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="ARN da State Machine do Step Functions",
            export_name=f"{self.stack_name}-StateMachineArn"
        )
        
        # State Machine Name
        CfnOutput(
            self,
            "StateMachineName",
            value=self.state_machine.state_machine_name,
            description="Nome da State Machine",
            export_name=f"{self.stack_name}-StateMachineName"
        )
        
        # SNS Topic ARNs
        CfnOutput(
            self,
            "SuccessTopicArn",
            value=self.success_topic.topic_arn,
            description="ARN do tópico SNS de sucesso",
            export_name=f"{self.stack_name}-SuccessTopicArn"
        )
        
        CfnOutput(
            self,
            "FailureTopicArn",
            value=self.failure_topic.topic_arn,
            description="ARN do tópico SNS de falhas",
            export_name=f"{self.stack_name}-FailureTopicArn"
        )
        
        CfnOutput(
            self,
            "AlertsTopicArn",
            value=self.alerts_topic.topic_arn,
            description="ARN do tópico SNS de alertas",
            export_name=f"{self.stack_name}-AlertsTopicArn"
        )
        
        # Schedule Names
        CfnOutput(
            self,
            "DailyScheduleName",
            value=self.daily_schedule.name,
            description="Nome do agendamento diário",
            export_name=f"{self.stack_name}-DailyScheduleName"
        )
        
        CfnOutput(
            self,
            "WeeklyScheduleName", 
            value=self.weekly_consolidation_schedule.name,
            description="Nome do agendamento semanal de consolidação",
            export_name=f"{self.stack_name}-WeeklyScheduleName"
        )