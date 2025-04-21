document.addEventListener('DOMContentLoaded', function() {
    // 初始化配置
    initConfig();

    // 标签切换
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // 防止事件冒泡
            e.stopPropagation();
            const tabId = this.getAttribute('data-tab');
            switchTab(tabId);
        });
    });

    // 上传提供商切换
    const uploadProviderSelect = document.getElementById('UPLOAD_PROVIDER');
    if (uploadProviderSelect) {
        uploadProviderSelect.addEventListener('change', function() {
            toggleProviderConfig(this.value);
        });
    }

    // 切换按钮事件
    const toggleSwitches = document.querySelectorAll('.toggle-switch');
    toggleSwitches.forEach(toggleSwitch => {
        toggleSwitch.addEventListener('click', function(e) {
            // 防止事件冒泡
            e.stopPropagation();
            const checkbox = this.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
            }
        });
    });

    // 保存按钮
    const saveBtn = document.getElementById('saveBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveConfig);
    }

    // 重置按钮
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetConfig);
    }

    // 滚动按钮
    window.addEventListener('scroll', toggleScrollButtons);

    // --- 新增：API Key 模态框和搜索相关 ---
    const apiKeyModal = document.getElementById('apiKeyModal');
    const addApiKeyBtn = document.getElementById('addApiKeyBtn');
    const closeApiKeyModalBtn = document.getElementById('closeApiKeyModalBtn');
    const cancelAddApiKeyBtn = document.getElementById('cancelAddApiKeyBtn');
    const confirmAddApiKeyBtn = document.getElementById('confirmAddApiKeyBtn');
    const apiKeyBulkInput = document.getElementById('apiKeyBulkInput');
    const apiKeySearchInput = document.getElementById('apiKeySearchInput');
    const bulkDeleteApiKeyBtn = document.getElementById('bulkDeleteApiKeyBtn'); // 新增
    const bulkDeleteApiKeyModal = document.getElementById('bulkDeleteApiKeyModal'); // 新增
    const closeBulkDeleteModalBtn = document.getElementById('closeBulkDeleteModalBtn'); // 新增
    const cancelBulkDeleteApiKeyBtn = document.getElementById('cancelBulkDeleteApiKeyBtn'); // 新增
    const confirmBulkDeleteApiKeyBtn = document.getElementById('confirmBulkDeleteApiKeyBtn'); // 新增
    const bulkDeleteApiKeyInput = document.getElementById('bulkDeleteApiKeyInput'); // 新增

    // --- 新增：重置确认模态框相关 ---
    const resetConfirmModal = document.getElementById('resetConfirmModal');
    const closeResetModalBtn = document.getElementById('closeResetModalBtn');
    const cancelResetBtn = document.getElementById('cancelResetBtn');
    const confirmResetBtn = document.getElementById('confirmResetBtn');
    // --- 结束：新增 ---


    // 打开模态框
    if (addApiKeyBtn) {
        addApiKeyBtn.addEventListener('click', () => {
            if (apiKeyModal) {
                apiKeyModal.classList.add('show');
            }
            if (apiKeyBulkInput) apiKeyBulkInput.value = ''; // 清空输入框
        });
    }

    // 关闭模态框 (X 按钮)
    if (closeApiKeyModalBtn) {
        closeApiKeyModalBtn.addEventListener('click', () => {
            if (apiKeyModal) {
                apiKeyModal.classList.remove('show');
            }
        });
    }

    // 关闭模态框 (取消按钮)
    if (cancelAddApiKeyBtn) {
        cancelAddApiKeyBtn.addEventListener('click', () => {
            if (apiKeyModal) {
                apiKeyModal.classList.remove('show');
            }
        });
    }

    // 点击模态框外部关闭 (处理两个模态框)
    window.addEventListener('click', (event) => {
        if (event.target == apiKeyModal) {
            apiKeyModal.classList.remove('show');
        }
        if (event.target == resetConfirmModal) {
            resetConfirmModal.classList.remove('show');
        }
        if (event.target == bulkDeleteApiKeyModal) { // 新增对批量删除模态框的处理
            bulkDeleteApiKeyModal.classList.remove('show');
        }
    });

    // 确认添加 API Key
    if (confirmAddApiKeyBtn) {
        confirmAddApiKeyBtn.addEventListener('click', handleBulkAddApiKeys);
    }

    // API Key 搜索 (稍后实现具体逻辑)
    if (apiKeySearchInput) {
        apiKeySearchInput.addEventListener('input', handleApiKeySearch);
    }

    // --- 新增：批量删除 API Key 相关事件 ---
    // 打开批量删除模态框
    if (bulkDeleteApiKeyBtn) {
        bulkDeleteApiKeyBtn.addEventListener('click', () => {
            if (bulkDeleteApiKeyModal) {
                bulkDeleteApiKeyModal.classList.add('show');
            }
            if (bulkDeleteApiKeyInput) bulkDeleteApiKeyInput.value = ''; // 清空输入框
        });
    }

    // 关闭批量删除模态框 (X 按钮)
    if (closeBulkDeleteModalBtn) {
        closeBulkDeleteModalBtn.addEventListener('click', () => {
            if (bulkDeleteApiKeyModal) {
                bulkDeleteApiKeyModal.classList.remove('show');
            }
        });
    }

    // 关闭批量删除模态框 (取消按钮)
    if (cancelBulkDeleteApiKeyBtn) {
        cancelBulkDeleteApiKeyBtn.addEventListener('click', () => {
            if (bulkDeleteApiKeyModal) {
                bulkDeleteApiKeyModal.classList.remove('show');
            }
        });
    }

    // 确认批量删除 API Key
    if (confirmBulkDeleteApiKeyBtn) {
        confirmBulkDeleteApiKeyBtn.addEventListener('click', handleBulkDeleteApiKeys);
    }
    // --- 结束：批量删除 API Key 相关 ---
    // --- 结束：API Key 相关 ---

    // --- 新增：重置确认模态框事件监听 (移到 DOMContentLoaded 内部) ---
    if (closeResetModalBtn) {
        closeResetModalBtn.addEventListener('click', () => {
            if (resetConfirmModal) {
                resetConfirmModal.classList.remove('show');
            }
        });
    }
    if (cancelResetBtn) {
        cancelResetBtn.addEventListener('click', () => {
            if (resetConfirmModal) {
                resetConfirmModal.classList.remove('show');
            }
        });
    }
    if (confirmResetBtn) {
        // 调用之前定义的 executeReset 函数
        confirmResetBtn.addEventListener('click', () => {
             if (resetConfirmModal) {
                 resetConfirmModal.classList.remove('show'); // 关闭模态框
             }
             executeReset(); // 执行重置逻辑
        });
    }
    // --- 结束：重置相关 ---

    // 移除了静态生成令牌按钮的事件监听器，现在按钮是动态生成的

    // 认证令牌生成按钮事件绑定
    const generateAuthTokenBtn = document.getElementById('generateAuthTokenBtn');
    const authTokenInput = document.getElementById('AUTH_TOKEN');
    if (generateAuthTokenBtn && authTokenInput) {
        generateAuthTokenBtn.addEventListener('click', function() {
            const newToken = generateRandomToken();
            authTokenInput.value = newToken;
            showNotification('已生成新认证令牌', 'success');
        });
    }

    // --- 修改：思考模型预算映射不再需要手动添加按钮 ---
    // const addBudgetMapItemBtn = document.getElementById('addBudgetMapItemBtn');
    // if (addBudgetMapItemBtn) {
    //     addBudgetMapItemBtn.addEventListener('click', addBudgetMapItem);
    // }
    // --- 结束：思考模型预算映射相关 ---

    // 添加事件委托，处理动态添加的 THINKING_MODELS 输入框的 input 事件
    const thinkingModelsContainer = document.getElementById('THINKING_MODELS_container');
    if (thinkingModelsContainer) {
        thinkingModelsContainer.addEventListener('input', function(event) {
            if (event.target && event.target.classList.contains('array-input') && event.target.closest('.array-item[data-model-id]')) {
                const modelInput = event.target;
                const modelId = modelInput.closest('.array-item').getAttribute('data-model-id');
                const budgetKeyInput = document.querySelector(`.map-key-input[data-model-id="${modelId}"]`);
                if (budgetKeyInput) {
                    budgetKeyInput.value = modelInput.value;
                }
            }
        });
    }


}); // <-- DOMContentLoaded 结束括号

// --- 新增：生成唯一ID ---
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}
// --- 结束：生成唯一ID ---


// 初始化配置
async function initConfig() {
    try {
        showNotification('正在加载配置...', 'info');
        const response = await fetch('/api/config');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const config = await response.json();

        // 确保数组字段有默认值
        if (!config.API_KEYS || !Array.isArray(config.API_KEYS) || config.API_KEYS.length === 0) {
            config.API_KEYS = ['请在此处输入 API 密钥'];
        }

        if (!config.ALLOWED_TOKENS || !Array.isArray(config.ALLOWED_TOKENS) || config.ALLOWED_TOKENS.length === 0) {
            config.ALLOWED_TOKENS = [''];
        }

        if (!config.IMAGE_MODELS || !Array.isArray(config.IMAGE_MODELS) || config.IMAGE_MODELS.length === 0) {
            config.IMAGE_MODELS = ['gemini-1.5-pro-latest'];
        }

        if (!config.SEARCH_MODELS || !Array.isArray(config.SEARCH_MODELS) || config.SEARCH_MODELS.length === 0) {
            config.SEARCH_MODELS = ['gemini-1.5-flash-latest'];
        }

        if (!config.FILTERED_MODELS || !Array.isArray(config.FILTERED_MODELS) || config.FILTERED_MODELS.length === 0) {
            config.FILTERED_MODELS = ['gemini-1.0-pro-latest'];
        }
        // --- 新增：处理新字段的默认值 ---
        if (!config.THINKING_MODELS || !Array.isArray(config.THINKING_MODELS)) {
            config.THINKING_MODELS = []; // 默认为空数组
        }
        if (!config.THINKING_BUDGET_MAP || typeof config.THINKING_BUDGET_MAP !== 'object' || config.THINKING_BUDGET_MAP === null) {
            config.THINKING_BUDGET_MAP = {}; // 默认为空对象
        }
        // --- 结束：处理新字段的默认值 ---

        populateForm(config);

        // 确保上传提供商有默认值
        const uploadProvider = document.getElementById('UPLOAD_PROVIDER');
        if (uploadProvider && !uploadProvider.value) {
            uploadProvider.value = 'smms'; // 设置默认值为 smms
            toggleProviderConfig('smms');
        }

        showNotification('配置加载成功', 'success');
    } catch (error) {
        console.error('加载配置失败:', error);
        showNotification('加载配置失败: ' + error.message, 'error');

        // 加载失败时，使用默认配置
        const defaultConfig = {
            API_KEYS: [''],
            ALLOWED_TOKENS: [''],
            IMAGE_MODELS: ['gemini-1.5-pro-latest'],
            SEARCH_MODELS: ['gemini-1.5-flash-latest'],
            FILTERED_MODELS: ['gemini-1.0-pro-latest'],
            UPLOAD_PROVIDER: 'smms',
            THINKING_MODELS: [],
            THINKING_BUDGET_MAP: {},
            S3_ACCESS_KEY: '',
            S3_SECRET_KEY: '',
            S3_ENDPOINT_URL: '',
            S3_REGION: 'us-east-1',
            S3_BUCKET_NAME: '',
            S3_URL_PREFIX: ''
        };

        populateForm(defaultConfig);
        toggleProviderConfig('smms');
    }
}

// 填充表单
function populateForm(config) {
    const modelIdMap = {}; // modelName -> modelId

    // 1. Clear existing dynamic content first
    const arrayContainers = document.querySelectorAll('.array-container');
    arrayContainers.forEach(container => {
        container.innerHTML = ''; // Clear all array containers
    });
    const budgetMapContainer = document.getElementById('THINKING_BUDGET_MAP_container');
    if (budgetMapContainer) {
        budgetMapContainer.innerHTML = ''; // Clear budget map container
    } else {
        console.error("Critical: THINKING_BUDGET_MAP_container not found!");
        return; // Cannot proceed
    }

    // 2. Populate THINKING_MODELS and build the map
    if (Array.isArray(config.THINKING_MODELS)) {
        const container = document.getElementById('THINKING_MODELS_container');
        if (container) {
            config.THINKING_MODELS.forEach(modelName => {
                if (modelName && typeof modelName === 'string' && modelName.trim()) {
                    const trimmedModelName = modelName.trim();
                    // Call addArrayItemWithValue to add the model DOM element and get its ID
                    const modelId = addArrayItemWithValue('THINKING_MODELS', trimmedModelName);
                    if (modelId) {
                        modelIdMap[trimmedModelName] = modelId;
                    } else {
                         console.warn(`Failed to get modelId for THINKING_MODEL: '${trimmedModelName}'`);
                    }
                } else {
                     console.warn(`Invalid THINKING_MODEL entry found:`, modelName);
                }
            });
        } else {
             console.error("Critical: THINKING_MODELS_container not found!");
        }
    }

    // 3. Populate THINKING_BUDGET_MAP using the map
    let budgetItemsAdded = false;
    if (config.THINKING_BUDGET_MAP && typeof config.THINKING_BUDGET_MAP === 'object') {
        for (const [modelName, budgetValue] of Object.entries(config.THINKING_BUDGET_MAP)) {
             if (modelName && typeof modelName === 'string') {
                const trimmedModelName = modelName.trim();
                const modelId = modelIdMap[trimmedModelName]; // Look up the ID
                if (modelId) {
                    // Call the function specifically designed to add ONLY the budget map DOM element
                    createAndAppendBudgetMapItem(trimmedModelName, budgetValue, modelId);
                    budgetItemsAdded = true;
                } else {
                    // Log if a budget entry exists but its corresponding model wasn't found/added
                    console.warn(`Budget map: Could not find model ID for '${trimmedModelName}'. Skipping budget item.`);
                }
            } else {
                 console.warn(`Invalid key found in THINKING_BUDGET_MAP:`, modelName);
            }
        }
    }
    // Add placeholder only if no budget items were successfully added
    if (!budgetItemsAdded && budgetMapContainer) {
         budgetMapContainer.innerHTML = '<div class="text-gray-500 text-sm italic">请在上方添加思考模型，预算将自动关联。</div>';
    }

    // 4. Populate other array fields (excluding THINKING_MODELS)
    for (const [key, value] of Object.entries(config)) {
        if (Array.isArray(value) && key !== 'THINKING_MODELS') {
            const container = document.getElementById(`${key}_container`);
            if (container) {
                // Container already cleared, just add items
                value.forEach(itemValue => {
                    if (typeof itemValue === 'string') {
                         addArrayItemWithValue(key, itemValue); // This adds non-thinking model array items
                    } else {
                         console.warn(`Invalid item found in array '${key}':`, itemValue);
                    }
                });
            }
        }
    }

    // 5. Populate non-array/non-budget fields
     for (const [key, value] of Object.entries(config)) {
        if (!Array.isArray(value) && !(typeof value === 'object' && value !== null && key === 'THINKING_BUDGET_MAP')) {
            const element = document.getElementById(key);
            if (element) {
                if (element.type === 'checkbox' && typeof value === 'boolean') {
                    element.checked = value;
                } else if (element.type !== 'checkbox') {
                    if (key === 'LOG_LEVEL' && typeof value === 'string') {
                        element.value = value.toUpperCase();
                    } else {
                        element.value = (value !== null && value !== undefined) ? value : '';
                    }
                }
            }
        }
    }

    // 6. Initialize upload provider
    const uploadProvider = document.getElementById('UPLOAD_PROVIDER');
    if (uploadProvider) {
        toggleProviderConfig(uploadProvider.value);
    }
}

// --- 新增：处理批量添加 API Key 的逻辑 ---
function handleBulkAddApiKeys() {
    const apiKeyBulkInput = document.getElementById('apiKeyBulkInput');
    const apiKeyContainer = document.getElementById('API_KEYS_container');
    const apiKeyModal = document.getElementById('apiKeyModal');

    if (!apiKeyBulkInput || !apiKeyContainer || !apiKeyModal) return;

    const bulkText = apiKeyBulkInput.value;
    const keyRegex = /AIzaSy\S{33}/g; // 全局匹配
    const extractedKeys = bulkText.match(keyRegex) || [];

    // 获取当前已有的 keys
    const currentKeyInputs = apiKeyContainer.querySelectorAll('.array-input');
    const currentKeys = Array.from(currentKeyInputs).map(input => input.value).filter(key => key.trim() !== '');

    // 合并并去重
    const combinedKeys = new Set([...currentKeys, ...extractedKeys]);
    const uniqueKeys = Array.from(combinedKeys);

    // 清空现有列表显示
    const existingItems = apiKeyContainer.querySelectorAll('.array-item');
    existingItems.forEach(item => item.remove());

    // 重新填充列表
    uniqueKeys.forEach(key => {
        addArrayItemWithValue('API_KEYS', key);
    });

    // 关闭模态框
    apiKeyModal.classList.remove('show');
    showNotification(`添加/更新了 ${uniqueKeys.length} 个唯一密钥`, 'success');
}

// --- 新增：处理 API Key 搜索的逻辑 ---
function handleApiKeySearch() {
    const apiKeySearchInput = document.getElementById('apiKeySearchInput');
    const apiKeyContainer = document.getElementById('API_KEYS_container');

    if (!apiKeySearchInput || !apiKeyContainer) return;

    const searchTerm = apiKeySearchInput.value.toLowerCase();
    const keyItems = apiKeyContainer.querySelectorAll('.array-item');

    keyItems.forEach(item => {
        const input = item.querySelector('.array-input');
        if (input) {
            const key = input.value.toLowerCase();
            if (key.includes(searchTerm)) {
                item.style.display = 'flex'; // 或者 'block'，取决于你的布局
            } else {
                item.style.display = 'none';
            }
        }
    });
}

// --- 新增：处理批量删除 API Key 的逻辑 ---
function handleBulkDeleteApiKeys() {
    const bulkDeleteTextarea = document.getElementById('bulkDeleteApiKeyInput'); // Use the textarea ID
    const apiKeyContainer = document.getElementById('API_KEYS_container');
    const bulkDeleteModal = document.getElementById('bulkDeleteApiKeyModal');

    if (!bulkDeleteTextarea || !apiKeyContainer || !bulkDeleteModal) return;

    const bulkText = bulkDeleteTextarea.value;
    if (!bulkText.trim()) {
        showNotification('请粘贴需要删除的 API 密钥', 'warning');
        return;
    }

    // Use the same regex as for adding keys to extract keys to delete
    const keyRegex = /AIzaSy\S{33}/g;
    const keysToDelete = new Set(bulkText.match(keyRegex) || []); // Create a Set for efficient lookup

    if (keysToDelete.size === 0) {
        showNotification('未在输入内容中提取到有效的 API 密钥格式', 'warning');
        // Optionally clear the textarea or keep it as is
        // bulkDeleteTextarea.value = '';
        return;
    }

    const keyItems = apiKeyContainer.querySelectorAll('.array-item');
    let deleteCount = 0;

    keyItems.forEach(item => {
        const input = item.querySelector('.array-input');
        // Check if the input exists and its value is in the set of keys to delete
        if (input && keysToDelete.has(input.value)) {
            item.remove(); // Remove the entire array item element
            deleteCount++;
        }
    });

    // Close the modal
    bulkDeleteModal.classList.remove('show');

    // Provide feedback
    if (deleteCount > 0) {
        showNotification(`成功删除了 ${deleteCount} 个匹配的密钥`, 'success');
    } else {
        // This message implies keys were extracted but not found in the current list
        showNotification('列表中未找到您输入的任何密钥进行删除', 'info');
    }

    // Clear the textarea after processing
    bulkDeleteTextarea.value = '';
}

// 切换标签
function switchTab(tabId) {
    // 更新标签按钮状态
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        if (button.getAttribute('data-tab') === tabId) {
            // 激活状态：主色背景，白色文字，添加阴影
            button.classList.remove('bg-white', 'bg-opacity-50', 'text-gray-700', 'hover:bg-opacity-70');
            button.classList.add('bg-primary-600', 'text-white', 'shadow-md');
        } else {
            // 非激活状态：白色背景，灰色文字，无阴影
            button.classList.remove('bg-primary-600', 'text-white', 'shadow-md');
            button.classList.add('bg-white', 'bg-opacity-50', 'text-gray-700', 'hover:bg-opacity-70');
        }
    });

    // 更新内容区域
    const sections = document.querySelectorAll('.config-section');
    sections.forEach(section => {
        if (section.id === `${tabId}-section`) {
            section.classList.add('active');
        } else {
            section.classList.remove('active');
        }
    });
}

// 切换上传提供商配置
function toggleProviderConfig(provider) {
    const providerConfigs = document.querySelectorAll('.provider-config');
    providerConfigs.forEach(config => {
        if (config.getAttribute('data-provider') === provider) {
            config.classList.add('active');
        } else {
            config.classList.remove('active');
        }
    });
}


// 添加数组项
function addArrayItem(key) {
    const container = document.getElementById(`${key}_container`);
    if (!container) return;

    const newItemValue = ''; // Start with an empty value for new items
    const modelId = addArrayItemWithValue(key, newItemValue); // Add the DOM element

    // If it's a thinking model, also add the corresponding budget map item
    if (key === 'THINKING_MODELS' && modelId) {
        createAndAppendBudgetMapItem(newItemValue, 0, modelId); // Default budget 0
    }
}

// 添加带值的数组项 (Adds array item DOM, returns modelId if it's a thinking model)
function addArrayItemWithValue(key, value) {
    const container = document.getElementById(`${key}_container`);
    if (!container) return null;

    const isThinkingModel = key === 'THINKING_MODELS';
    const modelId = isThinkingModel ? generateUUID() : null;

    const arrayItem = document.createElement('div');
    // 主容器使用 Flexbox
    arrayItem.className = 'array-item flex items-center mb-2 gap-2'; // 添加 gap-2 来分隔元素
    if (isThinkingModel) {
        arrayItem.setAttribute('data-model-id', modelId); // 添加ID属性
    }


    // 创建一个包装器 div 来包含输入框和生成按钮
    const inputWrapper = document.createElement('div');
    // 这个包装器占据主要空间，并使用 Flexbox
    inputWrapper.className = 'flex items-center flex-grow border border-gray-300 rounded-md focus-within:border-primary-500 focus-within:ring focus-within:ring-primary-200 focus-within:ring-opacity-50';

    const input = document.createElement('input');
    input.type = 'text';
    input.name = `${key}[]`;
    input.value = value;
    // 输入框占据包装器内的主要空间，移除边框和圆角，因为包装器已有
    input.className = 'array-input flex-grow px-3 py-2 border-none rounded-l-md focus:outline-none'; // 移除右侧圆角
    if (isThinkingModel) {
         input.setAttribute('data-model-id', modelId); // 添加ID属性
         input.placeholder = '思考模型名称'; // 添加占位符
    }


    inputWrapper.appendChild(input); // 将输入框添加到包装器

    // 只为 ALLOWED_TOKENS 添加生成按钮
    if (key === 'ALLOWED_TOKENS') {
        const generateBtn = document.createElement('button');
        generateBtn.type = 'button';
        // 按钮样式，放在输入框右侧，有背景和内边距，调整颜色
        generateBtn.className = 'generate-btn px-2 py-2 text-gray-500 hover:text-primary-600 focus:outline-none rounded-r-md bg-gray-100 hover:bg-gray-200 transition-colors'; // 添加背景和右侧圆角
        generateBtn.innerHTML = '<i class="fas fa-dice"></i>';
        generateBtn.title = '生成随机令牌';
        generateBtn.addEventListener('click', function() {
            const newToken = generateRandomToken();
            input.value = newToken;
            showNotification('已生成新令牌', 'success');
        });
        inputWrapper.appendChild(generateBtn); // 将生成按钮添加到包装器
    } else {
        // 如果不是 ALLOWED_TOKENS，确保输入框有右侧圆角
        input.classList.add('rounded-r-md');
    }

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    // 删除按钮样式，保持不变
    removeBtn.className = 'remove-btn text-gray-400 hover:text-red-500 focus:outline-none transition-colors duration-150';
    removeBtn.innerHTML = '<i class="fas fa-trash-alt"></i>';
    removeBtn.title = '删除';
    removeBtn.addEventListener('click', function() {
        const currentArrayItem = this.closest('.array-item');
        if (isThinkingModel) {
            const currentModelId = currentArrayItem.getAttribute('data-model-id');
            // 查找并删除对应的预算映射项
            const budgetMapItem = document.querySelector(`.map-item[data-model-id="${currentModelId}"]`);
            if (budgetMapItem) {
                budgetMapItem.remove();
                 // 检查预算映射容器是否为空，如果是，则添加回占位符
                const budgetContainer = document.getElementById('THINKING_BUDGET_MAP_container');
                if (budgetContainer && budgetContainer.children.length === 0) {
                    budgetContainer.innerHTML = '<div class="text-gray-500 text-sm italic">请在上方添加思考模型，预算将自动关联。</div>';
                }
            }
        }
        currentArrayItem.remove(); // 删除模型项本身
    });

    // 将包装器（包含输入框和可能的生成按钮）和删除按钮添加到主容器
    arrayItem.appendChild(inputWrapper);
    arrayItem.appendChild(removeBtn);

    // 插入到容器末尾
    container.appendChild(arrayItem);

    // 返回生成的 ID (如果是思考模型) 或 null
    return isThinkingModel ? modelId : null;
    // Note: This function no longer automatically calls createAndAppendBudgetMapItem
}


// --- 新增：专门用于创建和添加预算映射 DOM 元素 ---
function createAndAppendBudgetMapItem(mapKey, mapValue, modelId) {
   const container = document.getElementById('THINKING_BUDGET_MAP_container');
   if (!container) {
       console.error("Cannot add budget item: THINKING_BUDGET_MAP_container not found!");
       return;
   }

   // If container currently only has the placeholder, clear it
   const placeholder = container.querySelector('.text-gray-500.italic');
   // Check if the only child is the placeholder before clearing
   if (placeholder && container.children.length === 1 && container.firstChild === placeholder) {
       container.innerHTML = '';
   }

   const mapItem = document.createElement('div');
   mapItem.className = 'map-item flex items-center mb-2 gap-2';
   mapItem.setAttribute('data-model-id', modelId); // Add ID attribute

   // Key Input (Model Name) - Read-only
   const keyInput = document.createElement('input');
   keyInput.type = 'text';
   keyInput.value = mapKey;
   keyInput.placeholder = '模型名称 (自动关联)';
   keyInput.readOnly = true;
   keyInput.className = 'map-key-input flex-grow px-3 py-2 border border-gray-300 rounded-md focus:outline-none bg-gray-100 text-gray-500';
   keyInput.setAttribute('data-model-id', modelId);

   // Value Input (Budget) - Integer
   const valueInput = document.createElement('input');
   valueInput.type = 'number';
   // Ensure mapValue is treated as integer, default to 0 if invalid
   const intValue = parseInt(mapValue, 10);
   valueInput.value = isNaN(intValue) ? 0 : intValue;
   valueInput.placeholder = '预算 (整数)';
   valueInput.className = 'map-value-input w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:border-primary-500 focus:ring focus:ring-primary-200 focus:ring-opacity-50';
   valueInput.min = 0; // 添加最小值
   valueInput.max = 24576; // 添加最大值
   valueInput.addEventListener('input', function() {
        // 限制输入为0到24576之间的整数
        let value = this.value.replace(/[^0-9]/g, '');
        if (value !== '') {
            value = parseInt(value, 10);
            if (value < 0) value = 0;
            if (value > 24576) value = 24576;
        }
        this.value = value;
   });

   // Remove Button - Removed for budget map items
   // const removeBtn = document.createElement('button');
   // removeBtn.type = 'button';
   // removeBtn.className = 'remove-btn text-gray-300 cursor-not-allowed focus:outline-none'; // Kept original class for reference
   // removeBtn.innerHTML = '<i class="fas fa-trash-alt"></i>';
   // removeBtn.title = '请从上方模型列表删除';
   // removeBtn.disabled = true;

   mapItem.appendChild(keyInput);
   mapItem.appendChild(valueInput);
   // mapItem.appendChild(removeBtn); // Do not append the remove button

   container.appendChild(mapItem);
}
// --- 结束：专门的预算映射项创建函数 ---


// 收集表单数据
function collectFormData() {
    const formData = {};

    // 处理普通输入
    const inputs = document.querySelectorAll('input[type="text"], input[type="number"], select');
    inputs.forEach(input => {
        if (!input.name.includes('[]')) {
            if (input.type === 'number') {
                formData[input.name] = parseFloat(input.value);
            } else {
                // 确保 select 元素的值也被正确收集
                formData[input.name] = input.value;
            }
        }
    });

    // 处理复选框
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        formData[checkbox.name] = checkbox.checked;
    });

    // 处理数组
    const arrayContainers = document.querySelectorAll('.array-container');
    arrayContainers.forEach(container => {
        const key = container.id.replace('_container', '');
        const arrayInputs = container.querySelectorAll('.array-input');
        formData[key] = Array.from(arrayInputs).map(input => input.value).filter(value => value.trim() !== '');
    });

    // --- 新增：处理 THINKING_BUDGET_MAP ---
    const budgetMapContainer = document.getElementById('THINKING_BUDGET_MAP_container');
    if (budgetMapContainer) {
        formData['THINKING_BUDGET_MAP'] = {};
        const mapItems = budgetMapContainer.querySelectorAll('.map-item');
        mapItems.forEach(item => {
            const keyInput = item.querySelector('.map-key-input');
            const valueInput = item.querySelector('.map-value-input');
            if (keyInput && valueInput && keyInput.value.trim() !== '') {
                // 将预算值解析为整数
                const budgetValue = parseInt(valueInput.value, 10); // 使用基数10
                // 检查是否为有效数字，如果不是则默认为 0
                formData['THINKING_BUDGET_MAP'][keyInput.value.trim()] = isNaN(budgetValue) ? 0 : budgetValue;
            }
        });
    }
    // --- 结束：处理 THINKING_BUDGET_MAP ---

    return formData;
}

// 辅助函数：停止定时任务
async function stopScheduler() {
    try {
        const response = await fetch('/api/scheduler/stop', { method: 'POST' });
        if (!response.ok) {
            console.warn(`停止定时任务失败: ${response.status}`);
        } else {
            console.log('定时任务已停止');
        }
    } catch (error) {
        console.error('调用停止定时任务API时出错:', error);
    }
}

// 辅助函数：启动定时任务
async function startScheduler() {
    try {
        const response = await fetch('/api/scheduler/start', { method: 'POST' });
        if (!response.ok) {
            console.warn(`启动定时任务失败: ${response.status}`);
        } else {
            console.log('定时任务已启动');
        }
    } catch (error) {
        console.error('调用启动定时任务API时出错:', error);
    }
}

// 保存配置
async function saveConfig() {
    try {
        const formData = collectFormData();

        showNotification('正在保存配置...', 'info');

        // 1. 停止定时任务
        await stopScheduler();

        const response = await fetch('/api/config', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        // 移除居中的 saveStatus 提示

        showNotification('配置保存成功', 'success');

        // 3. 启动新的定时任务
        await startScheduler();

    } catch (error) {
        console.error('保存配置失败:', error);
        // 保存失败时，也尝试重启定时任务，以防万一
        await startScheduler();
        // 移除居中的 saveStatus 提示

        showNotification('保存配置失败: ' + error.message, 'error');
    }
}

// 重置配置 (现在只负责打开模态框)
function resetConfig(event) {
    // 阻止事件冒泡和默认行为
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    console.log('resetConfig called. Event target:', event ? event.target.id : 'No event');

    // 确保只有当事件来自重置按钮时才显示模态框
    if (!event || event.target.id === 'resetBtn' || event.currentTarget.id === 'resetBtn') {
        const resetConfirmModal = document.getElementById('resetConfirmModal');
        if (resetConfirmModal) {
            resetConfirmModal.classList.add('show');
        } else {
            // Fallback if modal doesn't exist for some reason
            console.error("Reset confirmation modal not found! Falling back to default confirm.");
            // Fallback to original confirm behavior
            if (!confirm('确定要重置所有配置吗？这将恢复到默认值。')) {
                return;
            }
            // If confirmed, proceed with the reset logic directly (less ideal)
            executeReset();
        }
    }
}

// --- 新增：将实际重置逻辑提取到一个单独的函数 ---
async function executeReset() {
    try {
        showNotification('正在重置配置...', 'info');

        // 1. 停止定时任务
        await stopScheduler();
        const response = await fetch('/api/config/reset', { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const config = await response.json();
        populateForm(config);
        showNotification('配置已重置为默认值', 'success');

        // 3. 启动新的定时任务
        await startScheduler();

    } catch (error) {
        console.error('重置配置失败:', error);
        showNotification('重置配置失败: ' + error.message, 'error');
        // 重置失败时，也尝试重启定时任务
        await startScheduler();
    }
}
// 显示通知
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;

    // 统一样式为黑色半透明，与 keys_status.js 保持一致
    notification.classList.remove('bg-danger-500');
    notification.classList.add('bg-black');
    notification.style.backgroundColor = 'rgba(0,0,0,0.8)';
    notification.style.color = '#fff';

    // 应用过渡效果
    notification.style.opacity = "1";
    notification.style.transform = "translate(-50%, 0)";

    // 设置自动消失
    setTimeout(() => {
        notification.style.opacity = "0";
        notification.style.transform = "translate(-50%, 10px)";
    }, 3000);
}

// 刷新页面
function refreshPage(button) {
    button.classList.add('loading');
    location.reload();
}

// 滚动到顶部
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// 滚动到底部
function scrollToBottom() {
    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth'
    });
}

// 切换滚动按钮显示
function toggleScrollButtons() {
    const scrollButtons = document.querySelector('.scroll-buttons');

    if (window.scrollY > 200) {
        scrollButtons.style.display = 'flex';
    } else {
        scrollButtons.style.display = 'none';
    }
}

// --- 新增：生成随机令牌函数 ---
function generateRandomToken() {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_';
    const length = 48;
    let result = 'sk-';
    const charactersLength = characters.length;
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
}
// --- 结束：生成随机令牌函数 ---

// --- 修改：添加思考模型预算映射项 (现在由添加思考模型触发) ---
// function addBudgetMapItem() {
//    // 不再需要手动添加
// }

// Deprecated: This function is now effectively replaced by createAndAppendBudgetMapItem
// for the initial population logic. It delegates to the new function if called.
function addBudgetMapItemWithValue(mapKey, mapValue, modelId) {
    // console.warn("Deprecated call to addBudgetMapItemWithValue, use createAndAppendBudgetMapItem instead for population.");
    // Delegate to the new function which handles DOM creation
    createAndAppendBudgetMapItem(mapKey, mapValue, modelId);
}
/* --- 结束：(addBudgetMapItemWithValue 已弃用) --- */
