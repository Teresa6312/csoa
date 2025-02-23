TASK_TYPE_AUTO = "Auto"
TASK_TYPE_FLOW = "Flow"
TASK_TYPE_MANUAL = "Manual"
TASK_TYPE_CHOICES = (
    (TASK_TYPE_AUTO, "Manual (task to created task instance by user manually)"),
    (
        TASK_TYPE_AUTO,
        "Auto (task to created task instance by system workflow to auto detact the next task)",
    ),
    (TASK_TYPE_FLOW, "Flow Task (task to created task instance by system workflow)"),
)

ROLE_CASE_OWNER = "Case Owner"

CASE_COMPLETED = "Completed"
CASE_CANCELLED = "Cancelled"
CASE_DRAFT = "Draft"
CASE_SUBMITTED = "Submitted"
CASE_INITIATED = "Initiated"


# company/department/team is for data control, not access control, like KYC and CMT, data owns by different depertment or teams
# if other company/department/team need to see the data or edit the data, he/she should have the data permission which is controled by Permission
# Page access is controled by Role
# APP defines the app data belongs to which company/department/team (some data may not have data control, some data required data control, etc.)
# if there is no data access control required, use [APP] control type in AppMenu

# [App Name] role only apply for specific application, so apps.count = 1, and this role is applicatable to which team/department/company that the user has permission to
# Normal [team/department/company] role is applicable for selected application, and this role is applicatable to which team/department/company that the user belongs to
# [team/department/company] manager role is applicable for selected application, and this role is applicatable to which team/department/company that the user belongs to
# team/department/company] role is applicable for selected application, and this role is applicatable to which team/department/company that the user has permission to

APP_NAME_ROLE_TYPE = 1
APP_NAME_ROLE_TYPE_NAME = "[App Name] role"
NORMAL_TEAM_ROLE_TYPE = 2
NORMAL_TEAM_ROLE_TYPE_NAME = "Normal Team role"
NORMAL_DEPARTMENT_ROLE_TYPE = 3
NORMAL_DEPARTMENT_ROLE_TYPE_NAME = "Normal Department role"
NORMAL_COMPANY_ROLE_TYPE = 4
NORMAL_COMPANY_ROLE_TYPE_NAME = "Normal Company role"
TEAM_MANAGER_ROLE_TYPE = 5
TEAM_MANAGER_ROLE_TYPE_NAME = "Team Manager role"
DEPARTMENT_MANAGER_ROLE_TYPE = 6
DEPARTMENT_MANAGER_ROLE_TYPE_NAME = "Department Manager role"
COMPANY_MANAGER_ROLE_TYPE = 7
COMPANY_MANAGER_ROLE_TYPE_NAME = "Company Manager role"
DEPARTMENT_SENIOR_ROLE_TYPE = 8
DEPARTMENT_SENIOR_ROLE_TYPE_NAME = "Department Senior role"
APP_TEAM_ROLE_TYPE = 9
APP_TEAM_ROLE_TYPE_NAME = "App Team role"
APP_DEPARTMENT_ROLE_TYPE = 10
APP_DEPARTMENT_ROLE_TYPE_NAME = "App Department role"
APP_COMPANY_ROLE_TYPE = 12
APP_COMPANY_ROLE_TYPE_NAME = "App Company role"

GROUP_TYPE_CHOICE = (
    (APP_NAME_ROLE_TYPE, APP_NAME_ROLE_TYPE_NAME),
    (NORMAL_TEAM_ROLE_TYPE, NORMAL_TEAM_ROLE_TYPE_NAME),
    (NORMAL_DEPARTMENT_ROLE_TYPE, NORMAL_DEPARTMENT_ROLE_TYPE_NAME),
    (NORMAL_COMPANY_ROLE_TYPE, NORMAL_COMPANY_ROLE_TYPE_NAME),
    (TEAM_MANAGER_ROLE_TYPE, TEAM_MANAGER_ROLE_TYPE_NAME),
    (DEPARTMENT_MANAGER_ROLE_TYPE, DEPARTMENT_MANAGER_ROLE_TYPE_NAME),
    (COMPANY_MANAGER_ROLE_TYPE, COMPANY_MANAGER_ROLE_TYPE_NAME),
    (DEPARTMENT_SENIOR_ROLE_TYPE, DEPARTMENT_SENIOR_ROLE_TYPE_NAME),
    (APP_TEAM_ROLE_TYPE, APP_TEAM_ROLE_TYPE_NAME),
    (APP_DEPARTMENT_ROLE_TYPE, APP_DEPARTMENT_ROLE_TYPE_NAME),
    (APP_COMPANY_ROLE_TYPE, APP_COMPANY_ROLE_TYPE_NAME),
)

ROLE_TEAM_GROUP_TYPE = [
    NORMAL_TEAM_ROLE_TYPE,
    TEAM_MANAGER_ROLE_TYPE,
    APP_TEAM_ROLE_TYPE,
]
ROLE_DEPARTMENT_GROUP_TYPE = [
    NORMAL_DEPARTMENT_ROLE_TYPE,
    DEPARTMENT_MANAGER_ROLE_TYPE,
    APP_DEPARTMENT_ROLE_TYPE,
    DEPARTMENT_SENIOR_ROLE_TYPE,
]
ROLE_COMPANY_GROUP_TYPE = [
    NORMAL_COMPANY_ROLE_TYPE,
    COMPANY_MANAGER_ROLE_TYPE,
    APP_COMPANY_ROLE_TYPE,
]
ROLE_BELONGS_GROUP_TYPE = [
    NORMAL_TEAM_ROLE_TYPE,
    NORMAL_DEPARTMENT_ROLE_TYPE,
    NORMAL_COMPANY_ROLE_TYPE,
    TEAM_MANAGER_ROLE_TYPE,
    DEPARTMENT_MANAGER_ROLE_TYPE,
]
ROLE_PERMS_GROUP_TYPE = [
    APP_TEAM_ROLE_TYPE,
    APP_DEPARTMENT_ROLE_TYPE,
    APP_COMPANY_ROLE_TYPE,
]
ROLE_TEAM_BELONGS_GROUP_TYPE = [NORMAL_TEAM_ROLE_TYPE, TEAM_MANAGER_ROLE_TYPE]
ROLE_DEPARTMENT_BELONGS_GROUP_TYPE = [
    NORMAL_DEPARTMENT_ROLE_TYPE,
    DEPARTMENT_MANAGER_ROLE_TYPE,
]
ROLE_COMPANY_BELONGS_GROUP_TYPE = [NORMAL_COMPANY_ROLE_TYPE]
ROLE_MANAGER_GROUP_TYPE = [TEAM_MANAGER_ROLE_TYPE, DEPARTMENT_MANAGER_ROLE_TYPE]


JSON_FORM_TEMPLATE_SCHEMA_PATH = r"\jsonForm\json_template_schema.json"
