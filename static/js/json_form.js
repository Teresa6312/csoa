// 全局存储待显示字段
const pendingFields = new Map();

const selectChoicesMaps = new Map();

const validationRules = new Map();

const formFields = new Map();

function addFormset(formsetPrefix) {
    var totalForms = document.querySelector(`#id_${formsetPrefix}-TOTAL_FORMS`);
    if (!totalForms) {
        console.error(`Element with id id_${formsetPrefix}-TOTAL_FORMS not found`);
        return;
    }
    var formCount = parseInt(totalForms.value);
    var formsetContainer = document.querySelector(`#${formsetPrefix}_formset`);

    if (!formsetContainer) {
        console.error(`Element with id ${formsetPrefix}_formset not found`);
        return;
    }

    var formsetTemplate = document.querySelector(`#${formsetPrefix}_formset .formset-form.template`);
    if (!formsetTemplate) {
        console.error(`Formset template with class .template not found`);
        return;
    }

    var newForm = formsetTemplate.cloneNode(true);
    var regex = new RegExp(`${formsetPrefix}-(\\d+|__prefix__)`, 'g');
    var newHtml = newForm.innerHTML.replace(regex, `${formsetPrefix}-${formCount}`);

    // Append the new formset HTML to the container
    var newFormset = document.createElement('div');
    newFormset.classList.add('formset-form');
    newFormset.innerHTML = newHtml;

    // Clear the values in the cloned form fields
    newFormset.querySelectorAll('input, select, textarea').forEach(input => input.value = '');

    formCount++;
    totalForms.value = formCount;
    formsetContainer.appendChild(newFormset);

    // Add remove button to the new formset
    var removeButton = document.createElement('button');
    removeButton.setAttribute('type', 'button');
    removeButton.classList.add('w3-red','w3-border-0', 'w3-padding');
    removeButton.textContent = 'Remove';
    removeButton.addEventListener('click', function() {
        removeFormset(newFormset);
    });
    newFormset.appendChild(removeButton);
}

function removeFormset(formsetForm) {
    let checkbox = formsetForm.querySelector('input[type="checkbox"][id$="-DELETE"]');
    if (checkbox) {
        checkbox.checked = true;
    }
    formsetForm.style.display = 'none';
}

function initializeForm(formConfig, className) {
    // 清空缓存
    pendingFields.clear();
    validationRules.clear();
    selectChoicesMaps.clear();
    formFields.clear();

    // 遍历所有表单配置
    formConfig.forEach(section => {
        const template = section.json_template;
        // 1. 初始化基础字段
        Object.entries(template).forEach(([fieldKey, config]) => {
            // initFieldVisibility(fieldKey, config);
            initChoicesMaps(config);
            initValidateRules(fieldKey, config);
            formFields.set(fieldKey, config);
        });
        Object.entries(template).forEach(([fieldKey, config]) => {
            // 2. 处理动态显示逻辑
            if (config.to_display_conditions ) {
                setupDisplayConditions(fieldKey, config, template);
            }
            // 3. 初始化联动选项 only applicable for select fields
            if (config.choices_map && config.choices ) {
                setupConnectedFields(fieldKey, config, template);
            }
        });
        
    });
    // set up validation for the form
    setupValidation(className)
}

// function initFieldVisibility(fieldKey, config) {
//     const container = document.getElementById(`${fieldKey}_container`);
//     if (!container) {
//         console.warn(`字段容器不存在: ${fieldKey}_container`);
//         return;
//     }
// }

function initValidateRules(fieldKey, config) {
    if (config.to_validate_conditions != null) {
        validationRules.set(fieldKey, config.to_validate_conditions)
    }
}

function initChoicesMaps(config) {
    if (config.choices_map != null) {
        const mapKey = config.choices_map.map_name;
        if (selectChoicesMaps.get(mapKey) == null) {
            setup_csrf()
            let map_url = createActionLink('map', '/0/', dictionary_url) //dictionary_url getDictionary('map', 'dict_country_province_city')
            map_url = createActionLink(mapKey, '/1-filter', map_url)
            result = getData(map_url)
            if (result['data'] != null && result['data'].length > 0) {
                selectChoicesMaps.set(mapKey, result['data'])
            } else {
                selectChoicesMaps.set(mapKey, [])
            }
        }
    }
}

function setupDisplayConditions(parentKey, parentConfig, allFields) {
    // 存储待显示字段
    parentConfig.to_display_conditions.forEach(condition => {
        const subField = condition.field;
        const subConfig = allFields[subField];
        if (!subConfig) {
            console.error(`No config for: ${subField}`);
            return;
        }

        const element = document.getElementById(`${subField}_container`);
        if (element) {
            pendingFields.set(subField, {
                element: element.cloneNode(true),
                conditions: condition
            });
        }
    });

    const triggerElement = document.getElementById(`${parentKey}_container`);
    // 绑定事件监听
    if (triggerElement) {
        updateDisplayedFields(parentKey, triggerElement, parentConfig, allFields)
        triggerElement.addEventListener('change', () => 
            updateDisplayedFields(parentKey, triggerElement, parentConfig, allFields)
        );
    }
}

function getInputValueFromContainer(triggerElement) {
    // 查找第一个输入元素（支持 input/select）
    const inputElement = triggerElement.querySelector('input, select, textarea');
    if (!inputElement) {
        console.error(`Container ${containerId} does not contain a valid input element`);
        return null;
    }
    switch(inputElement.tagName.toLowerCase()) {
        case 'input':
            if (inputElement.type === 'checkbox') {
                return inputElement.checked;
            }
            if (inputElement.type === 'radio') {
                const checkedRadio = container.querySelector('input[type="radio"]:checked');
                return checkedRadio ? checkedRadio.value : null;
            }
            return inputElement.value;

        case 'select':
            if(inputElement.multiple) {
                const selectedValues = [];
                for (let i = 0; i < inputElement.options.length; i++) {
                    const option = inputElement.options[i];
                    if (option.selected) {
                        selectedValues.push(option.value);
                    }
                }
                return selectedValues
            }

            return inputElement.value;

        case 'textarea':
        return inputElement.value;

        default:
        console.error('Does not support this type of input element type:', inputElement.tagName);
        return null;
    }
}

function updateDisplayedFields(parentKey, parentContainer, parentConfig) {
    const parentValue = getInputValueFromContainer(parentContainer);
    // 评估所有显示条件
    parentConfig.to_display_conditions.forEach(conditionConfig => {
        if (evaluateConditionGroup(parentValue, conditionConfig)) {
            console.log(conditionConfig, "Condition valid for:" , conditionConfig.field);
            showConditionalField(parentKey,conditionConfig.field);
        }
        else {
            const element = document.getElementById(`${conditionConfig.field}_container`);
            if (element) {
                element.remove();
            }
            console.log(conditionConfig,"Condition invalid for:", conditionConfig.field);
        }
    });
}

function evaluateConditionGroup(fieldValue, conditionConfig) {
    const conditions = conditionConfig.conditions || [];
    const logicalOp = conditionConfig.operator || 'AND';
    const results = conditions.map(cond => {
        return evaluateCondition(fieldValue, cond);
    });

    if ( results == null || results.length === 0) {
        return false;
    }
    return logicalOp === 'AND' 
        ? results.every(r => r) 
        : results.some(r => r);
}

// 增强条件评估函数
function evaluateCondition(value, condition) {
    console.log(condition.type, value, condition.comparison_operator, condition.compare_value);
    try {
        switch (condition.type) {
            case 'Comparison Operators':
                
                return handleComparison(
                    value,
                    condition.comparison_operator,
                    condition.compare_value
                );
            
            case 'String Operators':
                return handleStringOperation(
                    value,
                    condition.comparison_operator,
                    condition.compare_value
                );
            
            case 'Array Operators':  // 新增数组操作支持
                if (condition.comparison_operator.startsWith('-')){
                    return handleArrayOperation(
                        value,
                        condition.comparison_operator.replace('-', ''),
                        condition.compare_value
                    );
                }
                return handleArrayOperation(
                    condition.compare_value,
                    condition.comparison_operator,
                    value
                );

            // case 'Range Check':
            //     return handleRangeCheck(
            //         value,
            //         condition.min,
            //         condition.max
            //     );
            
            default:
                console.warn(`不支持的条件类型: ${condition.type}`);
                return false;
        }
    } catch (error) {
        console.error(`条件评估错误: ${error.message}`);
        return false;
    }
}

// 添加范围检查处理函数 Add range check handler
/**
 * 处理范围检查 / Handle range check
 * @param {*} value 输入值 / Input value
 * @param {number} min 最小值 / Minimum value
 * @param {number} max 最大值 / Maximum value
 * @returns {boolean} 是否在范围内 / Whether value is within range
 */
function handleRangeCheck(value, min, max) {
    // 类型转换和验证 Convert and validate input
    const numericValue = Number(value);
    if (isNaN(numericValue)) {
        console.warn('范围检查需要数值类型 / Range check requires numeric type');
        return false;
    }

    // 边界检查 Boundary check
    return numericValue >= min && numericValue <= max;
}

// 值比较处理器
function handleComparison(actual, operator, expected) {
    const numActual = Number(actual);
    const numExpected = Number(expected);
    

    const comparators = {
        '==': (a, b) => a == b,
        '!=': (a, b) => a != b,
        '>': (a, b) => numActual > numExpected,
        '>=': (a, b) => numActual >= numExpected,
        '<': (a, b) => numActual < numExpected,
        '<=': (a, b) => numActual <= numExpected,
        'in': (a, b) => b.includes(a)
    };
    return comparators[operator]?.(actual, expected) ?? false;
}

// 字符串操作处理器
function handleStringOperation(value, operator, expected) {
    const strValue = String(value).toLowerCase();
    const strExpected = String(expected).toLowerCase();
    
    const operators = {
        'includes': () => strValue.includes(strExpected),
        'startsWith': () => strValue.startsWith(strExpected),
        'endsWith': () => strValue.endsWith(strExpected),
        'equals': () => strValue === strExpected,
        'notEquals': () => !(strValue === strExpected)
    };
    return operators[operator]?.() ?? false;
}

/**
 * 处理数组操作 / Handle array operation
 * @param {*|Array} value 输入值（支持字符串或数组） / Input value (string or array)
 * @param {string} operator 操作符（支持 includes/excludes/any/all/equal） / Operator (includes/excludes/any/all/equal)
 * @param {Array} expectedArray 期望数组 / Expected array
 * @returns {boolean} 操作结果 / Operation result
 * 
 * 操作符说明 / Operator explanations:
 * - includes : 输入值存在于期望数组中 / Input value exists in expected array
 * - excludes : 输入值不存在于期望数组中 / Input value not in expected array
 * - any     : 输入值包含期望数组中的任意元素 / Input value contains ANY element from expected array
 * - all     : 输入值包含期望数组中的所有元素 / Input value contains ALL elements from expected array
 * - equal   : 输入数组与期望数组完全相等（元素相同） / Input array exactly matches expected array
 */
    function handleArrayOperation(value, operator, expectedArray) {
    // 类型检查：确保期望值是数组 / Type check: Ensure expected value is array
    if (!Array.isArray(expectedArray)) {
        console.warn('比较值应为数组类型 / Compare value should be array');
        return false;
    }

    // 统一处理输入值 / Process input value:
    // - 如果是数组则保持原样 / Keep as-is if input is already array
    // - 否则转为小写字符串 / Otherwise convert to lowercase string
    const processedValue = Array.isArray(value) 
        ? value 
        : String(value).toLowerCase();

    // 处理期望数组：全部转为小写字符串 / Process expected array: all to lowercase strings
    const processedArray = expectedArray.map(item => 
        String(item).toLowerCase()
    );

    // 操作符功能映射 / Operator function mapping:
    const operators = {
        /**
         * 包含检查 / Inclusion check
         * 示例 / Example:
         * - processedValue: 'china'
         * - processedArray: ['china', 'usa']
         * - 返回 true / returns true
         */
        'includes': () => Array.isArray(processedValue) ? processedValue.every(element => processedArray.includes(element)):processedArray.includes(processedValue),

        /**
         * 排除检查 / Exclusion check
         * 示例 / Example:
         * - processedValue: 'japan'
         * - processedArray: ['china', 'usa']
         * - 返回 true / returns true
         */
        'excludes': () => Array.isArray(processedValue) ? !processedValue.every(element => processedArray.includes(element)):!processedArray.includes(processedValue),

        /**
         * 任意元素包含检查 / Any element inclusion check
         * 示例 / Example:
         * - processedValue: 'hello china' (字符串模式 / string mode)
         * - processedArray: ['china', 'usa']
         * - 返回 true / returns true
         * 
         * - processedValue: ['apple', 'orange'] (数组模式 / array mode)
         * - processedArray: ['banana', 'apple']
         * - 返回 true / returns true
         */
        'any': () => processedArray.some(item => processedValue.includes(item)),

        /**
         * 全部元素包含检查 / All elements inclusion check
         * 示例 / Example:
         * - processedValue: 'china usa japan' (字符串模式 / string mode)
         * - processedArray: ['china', 'usa']
         * - 返回 true / returns true
         * 
         * - processedValue: ['apple', 'banana'] (数组模式 / array mode)
         * - processedArray: ['apple', 'banana', 'orange']
         * - 返回 false / returns false
         */
        'all': () => processedArray.every(item => 
            processedValue.includes(item)),

        /**
         * 完全相等检查 / Exact equality check
         * 示例 / Example:
         * - processedValue: ['china', 'usa']
         * - processedArray: ['china', 'usa']
         * - 返回 true / returns true
         * 
         * - processedValue: ['usa', 'china']
         * - processedArray: ['china', 'usa']
         * - 返回 false / returns false (顺序不同 / different order)
         */
        'equal':() =>{
            // 仅当输入值为数组时执行检查 / Only perform check when value is array
            if (!Array.isArray(processedValue)) return false;
            return processedArray.every(item => 
                processedValue.includes(item)) && processedValue.every(item => 
                processedArray.includes(item))
        }
    };
    return operators[operator]?.() ?? false;
}

// 显示条件字段
function showConditionalField(parentKey,fieldKey) {
    const cached = pendingFields.get(fieldKey);
    if (!cached) {
        console.warn(`未注册的条件字段 / Unregistered conditional field: ${fieldKey}`);
        return;
    }

    const clone = cached.element.cloneNode(true);
    clone.classList.add('dynamic-field');
    clone.style.display = 'block';

    const parent = document.getElementById(`${parentKey}_container`);
    const field = document.getElementById(`${fieldKey}_container`);

    if (!field) {
        parent.after(clone);
    }
}

// 联动选项处理
function setupConnectedFields(fieldKey, config, allFields) {
    const element = document.getElementById(`${fieldKey}_container`);
    if (!element) return;

    element.addEventListener('change', () => {
        const elementValue = getInputValueFromContainer(element);
        const connected_fields = config.choices_map['connected_fields'];
        if (!connected_fields) return;
        connected_fields.forEach(connectedField => {
            const connectedConfig = allFields[connectedField];
            if (!connectedConfig) return;
            updateOptions(elementValue, fieldKey,  config, connectedField, connectedConfig);
        });
    });
}

function updateOptions(fieldValue, fieldKey, fieldConfig, connectedField, connectedConfig) {
    const connectedBlock = document.getElementById(`${connectedField}_container`);
    // 查找第一个输入元素（支持 select）
    const connectedInputElement = connectedBlock.querySelector('select');
    if (!connectedInputElement) {
        console.error(`容器 ${containerId} 内未找到输入元素 / No input element found in container ${containerId}`);
        return null;
    }
    // 实际应从options_map获取动态数据
    const mapKey = fieldConfig.choices_map['map_key']
    const targetKey = connectedConfig.choices_map['map_key']
    const filters = {}
    filters[mapKey] = fieldValue
    let options = getOptionsFromMap(fieldConfig.choices_map['map_name'], filters, targetKey);
    connectedInputElement.innerHTML = '';
    if (connectedInputElement && options) {
        if (options.length > 1) {
            var option = document.createElement('option');
            option.text = "--Select--";
            option.value = "";
            connectedInputElement.appendChild(option);
        }
        options
            .map(opt =>{
                var option = document.createElement('option');
                option.value = opt;
                option.text = opt;
                connectedInputElement.appendChild(option);
            });
    }
}

function getOptionsFromMap(mapKey, filters, targetKey) {
    let map = selectChoicesMaps.get(mapKey);
    let result = []
    if (map != undefined && map.length > 0) {
        Object.entries(filters).forEach(([key, value]) => {
            map = map.filter(item =>  item[key] === value && item[targetKey] !== 'null' && item[targetKey] !== null && item[targetKey] !== '');
        });
        if (map.length > 0) {
            result = map.map(item => item[targetKey]);
        }
        return result.filter((value, index, array) => array.indexOf(value) === index);
    } else {
        return []
    }
}

// 修改validateForm方法
function validateForm() {
    let isValid = true;
    validationRules.forEach((configs, fieldKey) => {
        const parentContainer = document.getElementById(`${fieldKey}_container`);
        const parentValue = getInputValueFromContainer(parentContainer);

        configs.forEach(conditionConfig => {
            if (evaluateConditionGroup(parentValue, conditionConfig)) {
                const targetBlock = document.getElementById(`${conditionConfig.field}_container`);
                const targetValue = getInputValueFromContainer(targetBlock)
                console.log("rules:", conditionConfig.rules);
                conditionConfig.rules.forEach(rule => {
                    if (rule.type == 'range') {
                        const { min, max } = rule.value;
                        if (targetValue < min || targetValue > max) {
                            // 显示错误信息
                            const targetLabel = formFields.get(conditionConfig.field).label;
                            const parentLabel = formFields.get(fieldKey).label;
                            // createMessageBox(`${targetLabel} value must between ${min} and ${max} when ${parentLabel} is ${parentValue}` , 'error', );
                            createInputError(targetBlock, `${targetLabel} value must between ${min} and ${max} when ${parentLabel} is ${parentValue}`)
                            isValid = false;
                        }
                    }
                })
            }
        });
    });
    return isValid;
};

function setupValidation(formName) {
    const form = document.getElementById(formName); // Get the form element by ID

    if (form) { // Check if the form exists (important!)
        form.addEventListener('submit', (e) => {
            if (!validateForm()) { // Check the *negation* of validateForm()
                e.preventDefault(); // Prevent submission ONLY if validation fails
                return false; // Stop further event propagation (optional but good practice)
            } else {
                return true; // Allow form submission if validation passes
            }
        });
    } else {
        console.error("Form with ID '" + formName + "' not found.");
    }
}