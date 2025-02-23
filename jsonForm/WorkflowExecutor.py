import json
from django.db.models import Q
from base import constants
from base.util import get_model_class

import logging

logger = logging.getLogger("django")


class WorkflowExecutor:
    def execute(self, case, current_task):
        """
        Executes the workflow, handling both the start and middle stages.

        Args:
            case: The Case instance.
            current_task: The current Task instance to be executed.

        Returns:
            The next Task instance to be executed, or None if the workflow is complete.
        """
        application = case.form.application
        workflow_instance = case.workflow_instance
        TaskInstance = (
            case.get_task_instances_model()
        )  # Get the TaskInstance model from the Case model
        request_data = {}

        if current_task and current_task.task_type == constants.TASK_TYPE_AUTO:
            request_data = case.get_case_data_in_json()  # Get case data for auto tasks

        while current_task:  # Loop for chained auto tasks
            if current_task.task_type == constants.TASK_TYPE_AUTO:
                task_instance = TaskInstance.objects.create(  # Create a TaskInstance
                    workflow_instance=workflow_instance,
                    task=current_task,
                )
                next_task = self.execute_auto_task(
                    current_task, request_data, task_instance
                )  # Execute the auto task
                task_instance.is_active = False  # Deactivate the TaskInstance
                task_instance.save()  # Save the TaskInstance
                current_task = next_task  # Move to the next task
            elif current_task.task_type == constants.TASK_TYPE_FLOW:
                self.create_flow_task_instance(
                    application, case, current_task, workflow_instance
                )  # Handle flow task
                return current_task
            elif current_task.task_type == constants.TASK_TYPE_MANUAL:
                raise ValueError(
                    f"Next task should not be Manual Task, Manual Task is for user to create"
                )  # Manual tasks are user-created
            else:
                raise ValueError(
                    f"Unknown task type: {current_task.task_type}"
                )  # Handle unknown task types
        return None  # Workflow is complete

    def create_flow_task_instance(self, application, case, task, workflow_instance):
        """
        Creates TaskInstances for a flow task, assigning them to appropriate users/permissions.

        Args:
            application: The Application instance.
            case: The Case instance.
            task: The Task instance (flow task).
            workflow_instance: The WorkflowInstance.

        Returns:
            None
        """
        case.task_instances.clear()  # Clear existing task instances
        TaskInstance = case.get_task_instances_model()
        Permission = get_model_class("userManagement", "Permission")
        pers = []  # List to store Permission objects
        if task.assign_to_role is not None:
            per = Permission.get_assign_to_role(
                application, task.assign_to_role, case
            )  # Get Permission by role
            if per is not None:
                pers.append(per)
        elif task.assign_to is not None:
            pers = task.assign_to.all()  # Get Permissions directly
        if len(pers) == 0:
            raise ValueError(
                f"No user group was found to assign the task ({task.assign_to_role} or {task.assign_to}). If the task is assign to the case/request owner, it may has lost the access"
            )  # Handle no assignees

        logger.debug(pers)  # Log the assigned Permissions

        for per in pers:  # Create TaskInstance for each assignee
            if (
                task.assign_to_role is not None
                and task.assign_to_role.name == constants.ROLE_CASE_OWNER
            ):
                task_instance = TaskInstance.objects.create(
                    task=task,
                    assign_to=per,
                    workflow_instance=workflow_instance,
                    assign_to_user=case.created_by,
                )  # Assign to case owner
            else:
                team_support = (
                    per.team.first_support() if per.team else None
                )  # Get first support user in team
                task_instance = TaskInstance.objects.create(
                    task=task,
                    assign_to=per,
                    workflow_instance=workflow_instance,
                    assign_to_user=team_support,
                )  # Assign to Permission
            task_instance.save()
            case.task_instances.add(task_instance)  # Add task instance to case
        return None

    def get_first_task(self, workflow):
        """
        Gets the first task in a workflow.

        Args:
            workflow: The Workflow instance.

        Returns:
            The first Task instance, ordered by index.
        """
        return workflow.task_workflow.order_by("index").first()

    def get_priority_decision(self, case):
        """
        Gets the highest priority DecisionPoint associated with a Case.

        Args:
            case: The Case instance.

        Returns:
            The highest priority DecisionPoint, or None if none are found.
        Raises:
            ValueError: If an error occurs during the database query.
        """
        try:
            task_instances = case.task_instances.all()
            decision_points = []
            for task_instance in task_instances:
                if task_instance.decision_point:
                    decision_points.append(task_instance.decision_point)

            decision_points.sort(key=lambda dp: dp.priority)  # Sort by priority
            return (
                decision_points[0] if len(decision_points) > 0 else None
            )  # Return the highest priority or None
        except Exception as e:
            raise ValueError(f"An error occurred on case {case.pk}: {e}")

    def execute_auto_task(self, task, request_data, task_instance):
        """
        Executes an auto task, evaluating conditions and determining the next task.

        Args:
            task: The Task instance (auto task).
            request_data: The request data (from the Case).
            task_instance: The TaskInstance.

        Returns:
            The next Task instance, or None if no matching condition is found.
        """
        decision_points = task.decision_points_task.order_by(
            "priority"
        )  # Order by priority
        for dp in decision_points:
            if self.evaluate_condition(
                dp.condition, request_data, task_instance
            ):  # Evaluate the condition
                task_instance.decision_point = dp  # Assign the DecisionPoint

                try:  # Extract matched values for the comment
                    # Safely load JSON data.  Handles cases where the JSONField might be None or contain invalid JSON
                    if isinstance(
                        dp.condition, str
                    ):  # Check if it's a string (older Django versions might store JSON as strings)
                        condition_data = json.loads(dp.condition)  # Load JSON
                    if isinstance(
                        dp.condition, dict
                    ):  # Make sure it's a dictionary before merging
                        condition_data = dp.condition
                    matched_values = {}
                    if "conditions" in condition_data:
                        for cond in condition_data["conditions"]:
                            field_name = cond["field_name"]
                            if field_name in request_data:
                                matched_values[field_name] = request_data[field_name]
                    elif "field_name" in condition_data:
                        field_name = condition_data["field_name"]
                        if field_name in request_data:
                            matched_values[field_name] = request_data[field_name]

                    task_instance.comment = f"Condition: {dp.condition}, Matched Values: {json.dumps(matched_values)}"  # Add comment

                except json.JSONDecodeError as e:
                    task_instance.comment = f"[ERROR] Condition: {dp.condition}; Request_Data: {request_data}; Error:{e}"  # Error comment
                    logger.error(
                        f"Invalid JSON format in condition: {dp.condition}. Error: {e}"
                    )  # Log the error

                task_instance.save()  # Save immediately
                return dp.next_task  # Return next task
        task_instance.save()  # Save if no condition matches
        return None  # No matching condition

    def evaluate_condition(self, condition_json, request_data, task_instance):
        """
        Evaluates a condition against the request data.

        Args:
            condition_json: The JSON string representing the condition.
            request_data: The request data (from the Case).
            task_instance: The TaskInstance.

        Returns:
            True if the condition is met, False otherwise.
        """
        if not condition_json:
            return True  # Empty condition

        try:
            # Safely load JSON data.  Handles cases where the JSONField might be None or contain invalid JSON
            if isinstance(
                condition_json, str
            ):  # Check if it's a string (older Django versions might store JSON as strings)
                condition_data = json.loads(condition_json)  # Load JSON
            if isinstance(
                condition_json, dict
            ):  # Make sure it's a dictionary before merging
                condition_data = condition_json
        except json.JSONDecodeError as e:
            task_instance.comment = (
                f"[ERROR] Invalid Task Condition format json: {e}"  # Error comment
            )
            task_instance.save()
            logger.debug(
                f"Invalid Task Condition format json: {condition_json}. Error: {e}"
            )  # Log
            raise ValueError(
                f"Invalid Task Condition format json: {condition_json}. Error: {e}"
            )  # Raise error
            # return False

        q = Q()

        def build_query(cond):
            field_name = cond["field_name"]
            comparison_operator = cond["comparison_operator"]
            compare_value = cond.get(
                "compare_value"
            )  # 使用get方法，避免key不存在的错误
            actual_value = request_data.get(field_name)

            if actual_value is None and comparison_operator != "isnull":
                return (
                    Q()
                )  # 如果actual_value不存在，且不是isnull查询，则直接返回空Q对象

            kwargs = {}

            if comparison_operator == "in":
                if isinstance(compare_value, list):
                    kwargs = {f"{field_name}__in": compare_value}
                else:
                    task_instance.comment = f"[ERROR] Invalid Task Condition format {condition_json} Invalid compare_value for 'in' operator: {compare_value}"
                    task_instance.save()
                    logger.debug(
                        f"Invalid compare_value for 'in' operator: {compare_value} in condition: {cond}"
                    )  # 添加日志
                    return Q()
            elif comparison_operator == "range":
                if isinstance(compare_value, list) and len(compare_value) == 2:
                    kwargs = {f"{field_name}__range": compare_value}
                else:
                    task_instance.comment = f"[ERROR] Invalid Task Condition format {condition_json} Invalid compare_value for 'range' operator: {compare_value}"
                    task_instance.save()
                    return Q()
            elif comparison_operator == "isnull":
                kwargs = {
                    f"{field_name}__isnull": compare_value
                }  #  compare_value 应该为布尔值
            elif comparison_operator == "regex":
                kwargs = {f"{field_name}__regex": compare_value}
            elif comparison_operator == "iregex":
                kwargs = {f"{field_name}__iregex": compare_value}
            else:  # 其他比较运算符
                kwargs = {f"{field_name}__{comparison_operator}": compare_value}

            return Q(**kwargs)

        if "operator" in condition_data and "conditions" in condition_data:
            operator = condition_data["operator"].upper()  # 转换为大写，忽略大小写
            conditions = condition_data["conditions"]

            for condition in conditions:
                q_condition = build_query(condition)

                if operator == "AND":
                    q &= q_condition
                elif operator == "OR":
                    q |= q_condition
                elif operator == "NOT":
                    q = ~q_condition
                else:
                    task_instance.comment = f"[ERROR] Invalid Task Condition format {condition_json};Invalid operator: {operator}"
                    task_instance.save()
                    logger.error(
                        f"Invalid operator: {operator} in condition: {condition_json}"
                    )
                    return False
        elif (
            "field_name" in condition_data and "comparison_operator" in condition_data
        ):  # 兼容单个condition的情况
            q = build_query(condition_data)
        else:
            task_instance.comment = (
                f"[ERROR] Invalid Task Condition format {condition_json}"
            )
            task_instance.save()
            logger.error(f"Invalid operator: {operator} in condition: {condition_json}")
            return False

        if isinstance(request_data, dict):
            # 遍历 condition 中用到的字段，检查是否都在 request_data 中
            fields_in_condition = set()
            if "conditions" in condition_data:
                for cond in condition_data["conditions"]:
                    fields_in_condition.add(cond["field_name"])
            elif "field_name" in condition_data:
                fields_in_condition.add(condition_data["field_name"])
            for field in fields_in_condition:
                if field not in request_data:
                    return False  # 只要有一个字段不存在，就返回False
            return q.check(request_data)  # 直接使用 request_data 字典进行判断
        else:
            return False
