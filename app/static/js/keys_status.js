// 统计数据可视化交互效果

function copyToClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  } else {
    return new Promise((resolve, reject) => {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        const successful = document.execCommand("copy");
        document.body.removeChild(textArea);
        if (successful) {
          resolve();
        } else {
          reject(new Error("复制失败"));
        }
      } catch (err) {
        document.body.removeChild(textArea);
        reject(err);
      }
    });
  }
}

// API 调用辅助函数 (与 error_logs.js 中的版本类似)
async function fetchAPI(url, options = {}) {
  try {
    const response = await fetch(url, options);

    if (response.status === 204) {
      return null; // Indicate success with no content for DELETE etc.
    }

    let responseData;
    try {
      // Clone the response to allow reading it multiple times if needed (e.g., for text fallback)
      const clonedResponse = response.clone();
      responseData = await response.json();
    } catch (e) {
      // If JSON parsing fails, try to get text, especially if response wasn't ok
      if (!response.ok) {
        const textResponse = await response.text(); // Use original response for text
        throw new Error(
          textResponse ||
            `HTTP error! status: ${response.status} - ${response.statusText}`
        );
      }
      // If response is ok but not JSON, maybe return raw text or handle differently
      console.warn("Response was not JSON for URL:", url);
      // Consider returning text or null based on expected non-JSON success cases
      return await response.text(); // Example: return text for non-JSON success
    }

    if (!response.ok) {
      // Prefer error message from API response body (already parsed as JSON)
      const message =
        responseData?.detail ||
        responseData?.message ||
        responseData?.error ||
        `HTTP error! status: ${response.status}`;
      throw new Error(message);
    }

    return responseData; // Return parsed JSON data
  } catch (error) {
    console.error(
      "API Call Failed:",
      error.message,
      "URL:",
      url,
      "Options:",
      options
    );
    // Re-throw the error so the calling function knows the operation failed
    // Add more context if possible
    throw new Error(`API请求失败: ${error.message}`);
  }
}

// 添加统计项动画效果
function initStatItemAnimations() {
  const statItems = document.querySelectorAll(".stat-item");
  statItems.forEach((item) => {
    item.addEventListener("mouseenter", () => {
      item.style.transform = "scale(1.05)";
      const icon = item.querySelector(".stat-icon");
      if (icon) {
        icon.style.opacity = "0.2";
        icon.style.transform = "scale(1.1) rotate(0deg)";
      }
    });

    item.addEventListener("mouseleave", () => {
      item.style.transform = "";
      const icon = item.querySelector(".stat-icon");
      if (icon) {
        icon.style.opacity = "";
        icon.style.transform = "";
      }
    });
  });
}

// 获取指定类型区域内选中的密钥
function getSelectedKeys(type) {
  const checkboxes = document.querySelectorAll(
    `#${type}Keys .key-checkbox:checked`
  );
  return Array.from(checkboxes).map((cb) => cb.value);
}

// 更新指定类型区域的批量操作按钮状态和计数
function updateBatchActions(type) {
  const selectedKeys = getSelectedKeys(type);
  const count = selectedKeys.length;
  const batchActionsDiv = document.getElementById(`${type}BatchActions`);
  const selectedCountSpan = document.getElementById(`${type}SelectedCount`);
  const buttons = batchActionsDiv.querySelectorAll("button");

  if (count > 0) {
    batchActionsDiv.classList.remove("hidden");
    selectedCountSpan.textContent = count;
    buttons.forEach((button) => (button.disabled = false));
  } else {
    batchActionsDiv.classList.add("hidden");
    selectedCountSpan.textContent = "0";
    buttons.forEach((button) => (button.disabled = true));
  }

  // 更新全选复选框状态
  const selectAllCheckbox = document.getElementById(
    `selectAll${type.charAt(0).toUpperCase() + type.slice(1)}`
  );
  const allCheckboxes = document.querySelectorAll(`#${type}Keys .key-checkbox`);
  // 只有在有可见的 key 时才考虑全选状态
  const visibleCheckboxes = document.querySelectorAll(
    `#${type}Keys li:not([style*="display: none"]) .key-checkbox`
  );
  if (selectAllCheckbox && visibleCheckboxes.length > 0) {
    selectAllCheckbox.checked = count === visibleCheckboxes.length;
    selectAllCheckbox.indeterminate =
      count > 0 && count < visibleCheckboxes.length;
  } else if (selectAllCheckbox) {
    selectAllCheckbox.checked = false;
    selectAllCheckbox.indeterminate = false;
  }
}

// 全选/取消全选指定类型的密钥
function toggleSelectAll(type, isChecked) {
  const listElement = document.getElementById(`${type}Keys`);
  // Select checkboxes within LI elements that are NOT styled with display:none
  // This targets currently visible items based on filtering.
  const visibleCheckboxes = listElement.querySelectorAll(
    `li:not([style*="display: none"]) .key-checkbox`
  );

  visibleCheckboxes.forEach((checkbox) => {
    checkbox.checked = isChecked;
    const listItem = checkbox.closest("li[data-key]"); // Get the LI from the current DOM
    if (listItem) {
      listItem.classList.toggle("selected", isChecked);

      // Sync with master array
      const key = listItem.dataset.key;
      const masterList = type === "valid" ? allValidKeys : allInvalidKeys;
      if (masterList) {
        // Ensure masterList is defined
        const masterListItem = masterList.find((li) => li.dataset.key === key);
        if (masterListItem) {
          const masterCheckbox = masterListItem.querySelector(".key-checkbox");
          if (masterCheckbox) {
            masterCheckbox.checked = isChecked;
          }
        }
      }
    }
  });
  updateBatchActions(type);
}

// 复制选中的密钥
function copySelectedKeys(type) {
  const selectedKeys = getSelectedKeys(type);

  if (selectedKeys.length === 0) {
    showNotification("没有选中的密钥可复制", "warning");
    return;
  }

  const keysText = selectedKeys.join("\n");

  copyToClipboard(keysText)
    .then(() => {
      showNotification(
        `已成功复制 ${selectedKeys.length} 个选中的${
          type === "valid" ? "有效" : "无效"
        }密钥`
      );
    })
    .catch((err) => {
      console.error("无法复制文本: ", err);
      showNotification("复制失败，请重试", "error");
    });
}

// 单个复制保持不变
function copyKey(key) {
  copyToClipboard(key)
    .then(() => {
      showNotification(`已成功复制密钥`);
    })
    .catch((err) => {
      console.error("无法复制文本: ", err);
      showNotification("复制失败，请重试", "error");
    });
}

// showCopyStatus 函数已废弃。

async function verifyKey(key, button) {
  try {
    // 禁用按钮并显示加载状态
    button.disabled = true;
    const originalHtml = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 验证中';

    try {
      const data = await fetchAPI(`/gemini/v1beta/verify-key/${key}`, {
        method: "POST",
      });

      // 根据验证结果更新UI并显示模态提示框
      if (data && (data.success || data.status === "valid")) {
        // 验证成功，显示成功结果
        button.style.backgroundColor = "#27ae60";
        // 使用结果模态框显示成功消息
        showResultModal(true, "密钥验证成功");
        // 模态框关闭时会自动刷新页面
      } else {
        // 验证失败，显示失败结果
        const errorMsg = data.error || "密钥无效";
        button.style.backgroundColor = "#e74c3c";
        // 使用结果模态框显示失败消息，改为true以在关闭时刷新
        showResultModal(false, "密钥验证失败: " + errorMsg, true);
      }
    } catch (apiError) {
      console.error("密钥验证 API 请求失败:", apiError);
      showResultModal(false, `验证请求失败: ${apiError.message}`, true);
    } finally {
      // 1秒后恢复按钮原始状态 (如果页面不刷新)
      // 由于现在成功和失败都会刷新，这部分逻辑可以简化或移除
      // 但为了防止未来修改刷新逻辑，暂时保留，但可能不会执行
      setTimeout(() => {
        if (
          !document.getElementById("resultModal") ||
          document.getElementById("resultModal").classList.contains("hidden")
        ) {
          button.innerHTML = originalHtml;
          button.disabled = false;
          button.style.backgroundColor = "";
        }
      }, 1000);
    }
  } catch (error) {
    console.error("验证失败:", error);
    // 确保在捕获到错误时恢复按钮状态 (如果页面不刷新)
    // button.disabled = false; // 由 finally 处理或因刷新而无需处理
    // button.innerHTML = '<i class="fas fa-check-circle"></i> 验证';
    showResultModal(false, "验证处理失败: " + error.message, true); // 改为true以在关闭时刷新
  }
}

async function resetKeyFailCount(key, button) {
  try {
    // 禁用按钮并显示加载状态
    button.disabled = true;
    const originalHtml = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 重置中';

    const data = await fetchAPI(`/gemini/v1beta/reset-fail-count/${key}`, {
      method: "POST",
    });

    // 根据重置结果更新UI
    if (data.success) {
      showNotification("失败计数重置成功");
      // 成功时保留绿色背景一会儿
      button.style.backgroundColor = "#27ae60";
      // 稍后刷新页面
      setTimeout(() => location.reload(), 1000);
    } else {
      const errorMsg = data.message || "重置失败";
      showNotification("重置失败: " + errorMsg, "error");
      // 失败时保留红色背景一会儿
      button.style.backgroundColor = "#e74c3c";
      // 如果失败，1秒后恢复按钮
      setTimeout(() => {
        button.innerHTML = originalHtml;
        button.disabled = false;
        button.style.backgroundColor = "";
      }, 1000);
    }

    // 恢复按钮状态逻辑已移至成功/失败分支内
  } catch (apiError) {
    console.error("重置失败:", apiError);
    showNotification(`重置请求失败: ${apiError.message}`, "error");
    // 确保在捕获到错误时恢复按钮状态
    button.disabled = false;
    button.innerHTML = '<i class="fas fa-redo-alt"></i> 重置'; // 恢复原始图标和文本
    button.style.backgroundColor = ""; // 清除可能设置的背景色
  }
}

// 显示重置确认模态框 (基于选中的密钥)
function showResetModal(type) {
  const modalElement = document.getElementById("resetModal");
  const titleElement = document.getElementById("resetModalTitle");
  const messageElement = document.getElementById("resetModalMessage");
  const confirmButton = document.getElementById("confirmResetBtn");

  const selectedKeys = getSelectedKeys(type);
  const count = selectedKeys.length;

  // 设置标题和消息
  titleElement.textContent = "批量重置失败次数";
  if (count > 0) {
    messageElement.textContent = `确定要批量重置选中的 ${count} 个${
      type === "valid" ? "有效" : "无效"
    }密钥的失败次数吗？`;
    confirmButton.disabled = false; // 确保按钮可用
  } else {
    // 这个情况理论上不会发生，因为按钮在未选中时是禁用的
    messageElement.textContent = `请先选择要重置的${
      type === "valid" ? "有效" : "无效"
    }密钥。`;
    confirmButton.disabled = true;
  }

  // 设置确认按钮事件
  confirmButton.onclick = () => executeResetAll(type);

  // 显示模态框
  modalElement.classList.remove("hidden");
}

function closeResetModal() {
  document.getElementById("resetModal").classList.add("hidden");
}

// 触发显示模态框
function resetAllKeysFailCount(type, event) {
  // 阻止事件冒泡
  if (event) {
    event.stopPropagation();
  }

  // 显示模态确认框
  showResetModal(type);
}

// 关闭模态框并根据参数决定是否刷新页面
function closeResultModal(reload = true) {
  document.getElementById("resultModal").classList.add("hidden");
  if (reload) {
    location.reload(); // 操作完成后刷新页面
  }
}

// 显示操作结果模态框 (通用版本)
function showResultModal(success, message, autoReload = true) {
  const modalElement = document.getElementById("resultModal");
  const titleElement = document.getElementById("resultModalTitle");
  const messageElement = document.getElementById("resultModalMessage");
  const iconElement = document.getElementById("resultIcon");
  const confirmButton = document.getElementById("resultModalConfirmBtn");

  // 设置标题
  titleElement.textContent = success ? "操作成功" : "操作失败";

  // 设置图标
  if (success) {
    iconElement.innerHTML =
      '<i class="fas fa-check-circle text-success-500"></i>';
    iconElement.className = "text-6xl mb-3 text-success-500"; // 稍微增大图标
  } else {
    iconElement.innerHTML =
      '<i class="fas fa-times-circle text-danger-500"></i>';
    iconElement.className = "text-6xl mb-3 text-danger-500"; // 稍微增大图标
  }

  // 清空现有内容并设置新消息
  messageElement.innerHTML = ""; // 清空
  if (typeof message === "string") {
    // 对于普通字符串消息，保持原有逻辑
    const messageDiv = document.createElement("div");
    messageDiv.innerText = message; // 使用 innerText 防止 XSS
    messageElement.appendChild(messageDiv);
  } else if (message instanceof Node) {
    // 如果传入的是 DOM 节点，直接添加
    messageElement.appendChild(message);
  } else {
    // 其他类型转为字符串
    const messageDiv = document.createElement("div");
    messageDiv.innerText = String(message);
    messageElement.appendChild(messageDiv);
  }

  // 设置确认按钮点击事件
  confirmButton.onclick = () => closeResultModal(autoReload);

  // 显示模态框
  modalElement.classList.remove("hidden");
}

// 显示批量验证结果的专用模态框
function showVerificationResultModal(data) {
  const modalElement = document.getElementById("resultModal");
  const titleElement = document.getElementById("resultModalTitle");
  const messageElement = document.getElementById("resultModalMessage");
  const iconElement = document.getElementById("resultIcon");
  const confirmButton = document.getElementById("resultModalConfirmBtn");

  const successfulKeys = data.successful_keys || [];
  const failedKeys = data.failed_keys || {};
  const validCount = data.valid_count || 0;
  const invalidCount = data.invalid_count || 0;

  // 设置标题和图标
  titleElement.textContent = "批量验证结果";
  if (invalidCount === 0 && validCount > 0) {
    iconElement.innerHTML =
      '<i class="fas fa-check-double text-success-500"></i>';
    iconElement.className = "text-6xl mb-3 text-success-500";
  } else if (invalidCount > 0 && validCount > 0) {
    iconElement.innerHTML =
      '<i class="fas fa-exclamation-triangle text-warning-500"></i>';
    iconElement.className = "text-6xl mb-3 text-warning-500";
  } else if (invalidCount > 0 && validCount === 0) {
    iconElement.innerHTML =
      '<i class="fas fa-times-circle text-danger-500"></i>';
    iconElement.className = "text-6xl mb-3 text-danger-500";
  } else {
    // 都为 0 或其他情况
    iconElement.innerHTML = '<i class="fas fa-info-circle text-gray-500"></i>';
    iconElement.className = "text-6xl mb-3 text-gray-500";
  }

  // 构建详细内容
  messageElement.innerHTML = ""; // 清空

  const summaryDiv = document.createElement("div");
  summaryDiv.className = "text-center mb-4 text-lg";
  summaryDiv.innerHTML = `验证完成：<span class="font-semibold text-success-600">${validCount}</span> 个成功，<span class="font-semibold text-danger-600">${invalidCount}</span> 个失败。`;
  messageElement.appendChild(summaryDiv);

  // 成功列表
  if (successfulKeys.length > 0) {
    const successDiv = document.createElement("div");
    successDiv.className = "mb-3";
    const successHeader = document.createElement("div");
    successHeader.className = "flex justify-between items-center mb-1";
    successHeader.innerHTML = `<h4 class="font-semibold text-success-700">成功密钥 (${successfulKeys.length}):</h4>`;

    const copySuccessBtn = document.createElement("button");
    copySuccessBtn.className =
      "px-2 py-0.5 bg-green-100 hover:bg-green-200 text-green-700 text-xs rounded transition-colors";
    copySuccessBtn.innerHTML = '<i class="fas fa-copy mr-1"></i>复制全部';
    copySuccessBtn.onclick = (e) => {
      e.stopPropagation();
      copyToClipboard(successfulKeys.join("\n"))
        .then(() =>
          showNotification(
            `已复制 ${successfulKeys.length} 个成功密钥`,
            "success"
          )
        )
        .catch(() => showNotification("复制失败", "error"));
    };
    successHeader.appendChild(copySuccessBtn);
    successDiv.appendChild(successHeader);

    const successList = document.createElement("ul");
    successList.className =
      "list-disc list-inside text-sm text-gray-600 max-h-20 overflow-y-auto bg-gray-50 p-2 rounded border border-gray-200";
    successfulKeys.forEach((key) => {
      const li = document.createElement("li");
      li.className = "font-mono";
      // Store full key in dataset for potential future use, display masked
      li.dataset.fullKey = key;
      li.textContent =
        key.substring(0, 4) + "..." + key.substring(key.length - 4);
      successList.appendChild(li);
    });
    successDiv.appendChild(successList);
    messageElement.appendChild(successDiv);
  }

  // 失败列表
  if (Object.keys(failedKeys).length > 0) {
    const failDiv = document.createElement("div");
    failDiv.className = "mb-1"; // 减少底部边距
    const failHeader = document.createElement("div");
    failHeader.className = "flex justify-between items-center mb-1";
    failHeader.innerHTML = `<h4 class="font-semibold text-danger-700">失败密钥 (${
      Object.keys(failedKeys).length
    }):</h4>`;

    const copyFailBtn = document.createElement("button");
    copyFailBtn.className =
      "px-2 py-0.5 bg-red-100 hover:bg-red-200 text-red-700 text-xs rounded transition-colors";
    copyFailBtn.innerHTML = '<i class="fas fa-copy mr-1"></i>复制全部';
    const failedKeysArray = Object.keys(failedKeys); // Get array of failed keys
    copyFailBtn.onclick = (e) => {
      e.stopPropagation();
      copyToClipboard(failedKeysArray.join("\n"))
        .then(() =>
          showNotification(
            `已复制 ${failedKeysArray.length} 个失败密钥`,
            "success"
          )
        )
        .catch(() => showNotification("复制失败", "error"));
    };
    failHeader.appendChild(copyFailBtn);
    failDiv.appendChild(failHeader);

    const failList = document.createElement("ul");
    failList.className =
      "text-sm text-gray-600 max-h-32 overflow-y-auto bg-red-50 p-2 rounded border border-red-200 space-y-1"; // 增加最大高度和间距
    Object.entries(failedKeys).forEach(([key, error]) => {
      const li = document.createElement("li");
      // li.className = 'flex justify-between items-center'; // Restore original layout
      li.className = "flex flex-col items-start"; // Start with vertical layout

      const keySpanContainer = document.createElement("div");
      keySpanContainer.className = "flex justify-between items-center w-full"; // Ensure key and button are on the same line initially

      const keySpan = document.createElement("span");
      keySpan.className = "font-mono";
      // Store full key in dataset, display masked
      keySpan.dataset.fullKey = key;
      keySpan.textContent =
        key.substring(0, 4) + "..." + key.substring(key.length - 4);

      const detailsButton = document.createElement("button");
      detailsButton.className =
        "ml-2 px-2 py-0.5 bg-red-200 hover:bg-red-300 text-red-700 text-xs rounded transition-colors";
      detailsButton.innerHTML = '<i class="fas fa-info-circle mr-1"></i>详情';
      detailsButton.dataset.error = error; // 将错误信息存储在 data 属性中
      detailsButton.onclick = (e) => {
        e.stopPropagation(); // Prevent modal close
        const button = e.currentTarget;
        const listItem = button.closest("li");
        const errorMsg = button.dataset.error;
        const errorDetailsId = `error-details-${key.replace(
          /[^a-zA-Z0-9]/g,
          ""
        )}`; // Create unique ID
        let errorDiv = listItem.querySelector(`#${errorDetailsId}`);

        if (errorDiv) {
          // Collapse: Remove error div and reset li layout
          errorDiv.remove();
          // listItem.className = 'flex justify-between items-center'; // Restore original layout
          listItem.className = "flex flex-col items-start"; // Keep vertical layout
          button.innerHTML = '<i class="fas fa-info-circle mr-1"></i>详情'; // Restore button text
        } else {
          // Expand: Create and append error div, change li layout
          errorDiv = document.createElement("div");
          errorDiv.id = errorDetailsId;
          errorDiv.className =
            "w-full mt-1 pl-0 text-xs text-red-600 bg-red-50 p-1 rounded border border-red-100 whitespace-pre-wrap break-words"; // Adjusted padding
          errorDiv.textContent = errorMsg;
          listItem.appendChild(errorDiv);
          listItem.className = "flex flex-col items-start"; // Change layout to vertical
          button.innerHTML = '<i class="fas fa-chevron-up mr-1"></i>收起'; // Change button text
          // Move button to be alongside the keySpan for vertical layout (already done)
        }
      };

      keySpanContainer.appendChild(keySpan); // Add keySpan to container
      keySpanContainer.appendChild(detailsButton); // Add button to container
      li.appendChild(keySpanContainer); // Add container to list item
      failList.appendChild(li);
    });
    failDiv.appendChild(failList);
    messageElement.appendChild(failDiv);
  }

  // 设置确认按钮点击事件 - 总是自动刷新
  confirmButton.onclick = () => closeResultModal(true); // Always reload

  // 显示模态框
  modalElement.classList.remove("hidden");
}

async function executeResetAll(type) {
  try {
    // 关闭确认模态框
    closeResetModal();

    // 找到对应的重置按钮以显示加载状态
    const resetButton = document.querySelector(
      `button[data-reset-type="${type}"]`
    );
    if (!resetButton) {
      showResultModal(
        false,
        `找不到${type === "valid" ? "有效" : "无效"}密钥区域的批量重置按钮`,
        false
      ); // Don't reload if button not found
      return;
    }

    // 获取选中的密钥
    const keysToReset = getSelectedKeys(type);

    if (keysToReset.length === 0) {
      showNotification(
        `没有选中的${type === "valid" ? "有效" : "无效"}密钥可重置`,
        "warning"
      );
      return;
    }

    // 禁用按钮并显示加载状态
    resetButton.disabled = true;
    const originalHtml = resetButton.innerHTML;
    resetButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 重置中';

    try {
      const options = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keys: keysToReset, key_type: type }),
      };
      const data = await fetchAPI(
        `/gemini/v1beta/reset-selected-fail-counts`,
        options
      );

      // 根据重置结果显示模态框
      if (data.success) {
        const message =
          data.reset_count !== undefined
            ? `成功重置 ${data.reset_count} 个选中的${
                type === "valid" ? "有效" : "无效"
              }密钥的失败次数`
            : `成功重置 ${keysToReset.length} 个选中的密钥`;
        showResultModal(true, message); // 成功后刷新页面
      } else {
        const errorMsg = data.message || "批量重置失败";
        // 失败后不自动刷新页面，让用户看到错误信息
        showResultModal(false, "批量重置失败: " + errorMsg, false);
      }
    } catch (apiError) {
      console.error("批量重置 API 请求失败:", apiError);
      showResultModal(false, `批量重置请求失败: ${apiError.message}`, false);
    } finally {
      // 恢复按钮状态 (仅在不刷新的情况下)
      if (
        !document.getElementById("resultModal") ||
        document.getElementById("resultModal").classList.contains("hidden") ||
        document.getElementById("resultModalTitle").textContent.includes("失败")
      ) {
        resetButton.innerHTML = originalHtml;
        resetButton.disabled = false;
      }
    }
  } catch (error) {
    console.error("批量重置处理失败:", error);
    showResultModal(false, "批量重置处理失败: " + error.message, false); // 失败后不自动刷新
  }
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function scrollToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
}

// 移除这个函数，因为它可能正在干扰按钮的显示
// HTML中已经设置了滚动按钮为flex显示，不需要JavaScript额外控制
// function updateScrollButtons() {
//     // 不执行任何操作
// }

function refreshPage(button) {
  button.classList.add("loading"); // Maybe add a loading class for visual feedback
  button.disabled = true;
  const icon = button.querySelector("i");
  if (icon) icon.classList.add("fa-spin"); // Add spin animation

  setTimeout(() => {
    window.location.reload();
    // No need to remove loading/spin as page reloads
  }, 300);
}

// 展开/收起区块内容的函数，带有平滑动画效果。
// @param {HTMLElement} header - 被点击的区块头部元素。
// @param {string} sectionId - (当前未使用，但可用于更精确的目标定位) 关联内容区块的ID。
function toggleSection(header, sectionId) {
  const toggleIcon = header.querySelector(".toggle-icon");
  // 内容元素是卡片内的 .key-content div
  const card = header.closest(".stats-card");
  const content = card ? card.querySelector(".key-content") : null;

  // 批量操作栏和分页控件也可能影响内容区域的动画高度计算
  const batchActions = card ? card.querySelector('[id$="BatchActions"]') : null;
  const pagination = card
    ? card.querySelector('[id$="PaginationControls"]')
    : null;

  if (!toggleIcon || !content) {
    console.error(
      "Toggle section failed: Icon or content element not found. Header:",
      header,
      "SectionId:",
      sectionId
    );
    return;
  }

  const isCollapsed = content.classList.contains("collapsed");
  toggleIcon.classList.toggle("collapsed", !isCollapsed); // 更新箭头图标方向

  if (isCollapsed) {
    // --- 准备展开动画 ---
    content.classList.remove("collapsed"); // 移除 collapsed 类以应用展开的样式

    // 步骤 1: 重置内联样式，让CSS控制初始的"隐藏"状态 (通常是 maxHeight: 0, opacity: 0)。
    //         同时，确保 overflow 在动画开始前是 hidden。
    content.style.maxHeight = ""; // 清除可能存在的内联 maxHeight
    content.style.opacity = ""; // 清除可能存在的内联 opacity
    content.style.paddingTop = ""; // 清除内联 padding
    content.style.paddingBottom = "";
    content.style.overflow = "hidden"; // 动画过程中隐藏溢出内容

    // 步骤 2: 使用 requestAnimationFrame (rAF) 确保浏览器在计算 scrollHeight 之前
    //         已经应用了上一步的样式重置（特别是如果CSS中有过渡效果）。
    requestAnimationFrame(() => {
      // 步骤 3: 计算内容区的目标高度。
      //         这包括内容本身的 scrollHeight，以及任何可见的批量操作栏和分页控件的高度。
      let targetHeight = content.scrollHeight;

      if (batchActions && !batchActions.classList.contains("hidden")) {
        targetHeight += batchActions.offsetHeight;
      }
      if (pagination && pagination.offsetHeight > 0) {
        // 尝试获取分页控件的 margin-top，以获得更精确的高度
        const paginationStyle = getComputedStyle(pagination);
        const paginationMarginTop = parseFloat(paginationStyle.marginTop) || 0;
        targetHeight += pagination.offsetHeight + paginationMarginTop;
      }

      // 步骤 4: 设置 maxHeight 和 opacity 以触发CSS过渡到展开状态。
      content.style.maxHeight = targetHeight + "px";
      content.style.opacity = "1";
      // 假设展开后的 padding 为 1rem (p-4 in Tailwind). 根据实际情况调整。
      content.style.paddingTop = "1rem";
      content.style.paddingBottom = "1rem";

      // 步骤 5: 监听 transitionend 事件。动画结束后，移除 maxHeight 以允许内容动态调整，
      //         并将 overflow 设置为 visible，以防内容变化后被裁剪。
      content.addEventListener(
        "transitionend",
        function onExpansionEnd() {
          content.removeEventListener("transitionend", onExpansionEnd); // 清理监听器
          // 再次检查确保是在展开状态 (避免在快速连续点击时出错)
          if (!content.classList.contains("collapsed")) {
            content.style.maxHeight = ""; // 允许内容自适应高度
            content.style.overflow = "visible"; // 允许内容溢出（如果需要）
          }
        },
        { once: true }
      ); // 确保监听器只执行一次
    });
  } else {
    // --- 准备收起动画 ---
    // 步骤 1: 获取当前内容区的可见高度。
    //         这对于从当前渲染高度平滑过渡到0是必要的。
    let currentVisibleHeight = content.scrollHeight; // scrollHeight 应该已经是包括padding的内部高度
    if (batchActions && !batchActions.classList.contains("hidden")) {
      currentVisibleHeight += batchActions.offsetHeight;
    }
    if (pagination && pagination.offsetHeight > 0) {
      const paginationStyle = getComputedStyle(pagination);
      const paginationMarginTop = parseFloat(paginationStyle.marginTop) || 0;
      currentVisibleHeight += pagination.offsetHeight + paginationMarginTop;
    }

    // 步骤 2: 将 maxHeight 设置为当前计算的可见高度，以确保过渡从当前高度开始。
    //         同时，确保 overflow 在动画开始前是 hidden。
    content.style.maxHeight = currentVisibleHeight + "px";
    content.style.overflow = "hidden";

    // 步骤 3: 使用 requestAnimationFrame (rAF) 确保浏览器应用了上述 maxHeight。
    requestAnimationFrame(() => {
      // 步骤 4: 过渡到目标状态 (收起): maxHeight 和 padding 设为0，opacity 设为0。
      content.style.maxHeight = "0px";
      content.style.opacity = "0";
      content.style.paddingTop = "0";
      content.style.paddingBottom = "0";
      // 在动画开始（或即将开始）后添加 collapsed 类，以便CSS可以应用最终的折叠样式。
      content.classList.add("collapsed");
    });
  }
}

// filterValidKeys 函数已被 filterAndSearchValidKeys 替代，此函数保留为空或可移除
function filterValidKeys() {
  // This function is now handled by filterAndSearchValidKeys
  // Kept for now to avoid breaking any potential legacy calls, but should be removed later.
  filterAndSearchValidKeys();
}

// --- Initialization Helper Functions ---
function initializePageAnimationsAndEffects() {
  initStatItemAnimations(); // Already an external function

  const animateCounters = () => {
    const statValues = document.querySelectorAll(".stat-value");
    statValues.forEach((valueElement) => {
      const finalValue = parseInt(valueElement.textContent, 10);
      if (!isNaN(finalValue)) {
        if (!valueElement.dataset.originalValue) {
          valueElement.dataset.originalValue = valueElement.textContent;
        }
        let startValue = 0;
        const duration = 1500;
        const startTime = performance.now();
        const updateCounter = (currentTime) => {
          const elapsedTime = currentTime - startTime;
          if (elapsedTime < duration) {
            const progress = elapsedTime / duration;
            const easeOutValue = 1 - Math.pow(1 - progress, 3);
            const currentValue = Math.floor(easeOutValue * finalValue);
            valueElement.textContent = currentValue;
            requestAnimationFrame(updateCounter);
          } else {
            valueElement.textContent = valueElement.dataset.originalValue;
          }
        };
        requestAnimationFrame(updateCounter);
      }
    });
  };
  setTimeout(animateCounters, 300);

  document.querySelectorAll(".stats-card").forEach((card) => {
    card.addEventListener("mouseenter", () => {
      card.classList.add("shadow-lg");
      card.style.transform = "translateY(-2px)";
    });
    card.addEventListener("mouseleave", () => {
      card.classList.remove("shadow-lg");
      card.style.transform = "";
    });
  });
}

function initializeSectionToggleListeners() {
  document.querySelectorAll(".stats-card-header").forEach((header) => {
    if (header.querySelector(".toggle-icon")) {
      header.addEventListener("click", (event) => {
        if (event.target.closest("input, label, button, select")) {
          return;
        }
        const card = header.closest(".stats-card");
        const content = card ? card.querySelector(".key-content") : null;
        const sectionId = content ? content.id : null;
        if (sectionId) {
          toggleSection(header, sectionId);
        } else {
          console.warn("Could not determine sectionId for toggle.");
        }
      });
    }
  });
}

function initializeKeyFilterControls() {
  const thresholdInput = document.getElementById("failCountThreshold");
  if (thresholdInput) {
    thresholdInput.addEventListener("input", filterValidKeys);
  }
}

function initializeGlobalBatchVerificationHandlers() {
  window.showVerifyModal = function (type, event) {
    if (event) {
      event.stopPropagation();
    }
    const modalElement = document.getElementById("verifyModal");
    const titleElement = document.getElementById("verifyModalTitle");
    const messageElement = document.getElementById("verifyModalMessage");
    const confirmButton = document.getElementById("confirmVerifyBtn");
    const selectedKeys = getSelectedKeys(type);
    const count = selectedKeys.length;
    titleElement.textContent = "批量验证密钥";
    if (count > 0) {
      messageElement.textContent = `确定要批量验证选中的 ${count} 个${
        type === "valid" ? "有效" : "无效"
      }密钥吗？此操作可能需要一些时间。`;
      confirmButton.disabled = false;
    } else {
      messageElement.textContent = `请先选择要验证的${
        type === "valid" ? "有效" : "无效"
      }密钥。`;
      confirmButton.disabled = true;
    }
    confirmButton.onclick = () => executeVerifyAll(type);
    modalElement.classList.remove("hidden");
  };

  window.closeVerifyModal = function () {
    document.getElementById("verifyModal").classList.add("hidden");
  };

  // executeVerifyAll 变为 initializeGlobalBatchVerificationHandlers 的局部函数
  async function executeVerifyAll(type) {
    // Removed window.
    try {
      window.closeVerifyModal(); // Calls the global close function, which is fine.
      const verifyButton = document.querySelector(
        `#${type}BatchActions button:nth-child(1)`
      ); // Assuming verify is the first button
      let originalVerifyHtml = "";
      if (verifyButton) {
        originalVerifyHtml = verifyButton.innerHTML;
        verifyButton.disabled = true;
        verifyButton.innerHTML =
          '<i class="fas fa-spinner fa-spin"></i> 验证中';
      }
      const keysToVerify = getSelectedKeys(type);
      if (keysToVerify.length === 0) {
        showNotification(
          `没有选中的${type === "valid" ? "有效" : "无效"}密钥可验证`,
          "warning"
        );
        if (verifyButton) {
          // Restore button if no keys selected
          verifyButton.innerHTML = originalVerifyHtml;
        }
        return;
      }
      showNotification("开始批量验证，请稍候...", "info");
      const options = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keys: keysToVerify }),
      };
      const data = await fetchAPI(
        `/gemini/v1beta/verify-selected-keys`,
        options
      );
      if (data) {
        showVerificationResultModal(data);
      } else {
        throw new Error("API did not return verification data.");
      }
    } catch (apiError) {
      console.error("批量验证处理失败:", apiError);
      showResultModal(false, `批量验证处理失败: ${apiError.message}`, true);
    } finally {
      console.log("Bulk verification process finished.");
      // Button state will be reset on page reload or by updateBatchActions
    }
  }
  // The confirmButton.onclick in showVerifyModal (defined earlier in initializeGlobalBatchVerificationHandlers)
  // will correctly reference this local executeVerifyAll due to closure.
}

function initializeKeySelectionListeners() {
  const setupEventListenersForList = (listId, keyType) => {
    const listElement = document.getElementById(listId);
    if (!listElement) return;

    // Event delegation for clicks on list items to toggle checkbox
    listElement.addEventListener("click", (event) => {
      const listItem = event.target.closest("li[data-key]");
      if (!listItem) return;

      // Do not toggle if a button, a link, or any element explicitly designed for interaction within the li was clicked
      if (
        event.target.closest(
          "button, a, input[type='button'], input[type='submit']"
        )
      ) {
        let currentTarget = event.target;
        let isInteractiveElementClick = false;
        while (currentTarget && currentTarget !== listItem) {
          if (
            currentTarget.tagName === "BUTTON" ||
            currentTarget.tagName === "A" ||
            (currentTarget.tagName === "INPUT" &&
              ["button", "submit"].includes(currentTarget.type))
          ) {
            isInteractiveElementClick = true;
            break;
          }
          currentTarget = currentTarget.parentElement;
        }
        if (isInteractiveElementClick) return;
      }

      const checkbox = listItem.querySelector(".key-checkbox");
      if (checkbox) {
        checkbox.checked = !checkbox.checked;
        checkbox.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });

    // Event delegation for 'change' event on checkboxes within the list
    listElement.addEventListener("change", (event) => {
      if (event.target.classList.contains("key-checkbox")) {
        const checkbox = event.target; // This is the checkbox in the DOM
        const listItem = checkbox.closest("li[data-key]"); // This is the LI in the DOM

        if (listItem) {
          listItem.classList.toggle("selected", checkbox.checked);

          // Sync with master array
          const key = listItem.dataset.key;
          const masterList =
            keyType === "valid" ? allValidKeys : allInvalidKeys;
          if (masterList) {
            // Ensure masterList is defined
            const masterListItem = masterList.find(
              (li) => li.dataset.key === key
            );
            if (masterListItem) {
              const masterCheckbox =
                masterListItem.querySelector(".key-checkbox");
              if (masterCheckbox) {
                masterCheckbox.checked = checkbox.checked;
              }
            }
          }
        }
        updateBatchActions(keyType);
      }
    });
  };

  setupEventListenersForList("validKeys", "valid");
  setupEventListenersForList("invalidKeys", "invalid");
}

function initializeAutoRefreshControls() {
  const autoRefreshToggle = document.getElementById("autoRefreshToggle");
  const autoRefreshIntervalTime = 60000; // 60秒
  let autoRefreshTimer = null;

  function startAutoRefresh() {
    if (autoRefreshTimer) return;
    console.log("启动自动刷新...");
    showNotification("自动刷新已启动", "info", 2000);
    autoRefreshTimer = setInterval(() => {
      console.log("自动刷新 keys_status 页面...");
      location.reload();
    }, autoRefreshIntervalTime);
  }

  function stopAutoRefresh() {
    if (autoRefreshTimer) {
      console.log("停止自动刷新...");
      showNotification("自动刷新已停止", "info", 2000);
      clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  }

  if (autoRefreshToggle) {
    const isAutoRefreshEnabled =
      localStorage.getItem("autoRefreshEnabled") === "true";
    autoRefreshToggle.checked = isAutoRefreshEnabled;
    if (isAutoRefreshEnabled) {
      startAutoRefresh();
    }
    autoRefreshToggle.addEventListener("change", () => {
      if (autoRefreshToggle.checked) {
        localStorage.setItem("autoRefreshEnabled", "true");
        startAutoRefresh();
      } else {
        localStorage.setItem("autoRefreshEnabled", "false");
        stopAutoRefresh();
      }
    });
  }
}

// These variables are used by pagination and search, define them in a scope accessible by initializeKeyPaginationAndSearch
let allValidKeys = [];
let allInvalidKeys = [];
let filteredValidKeys = [];
let itemsPerPage = 10; // Default
let validCurrentPage = 1; // Also used by displayPage
let invalidCurrentPage = 1; // Also used by displayPage

function initializeKeyPaginationAndSearch() {
  const validKeysListElement = document.getElementById("validKeys");
  const invalidKeysListElement = document.getElementById("invalidKeys");
  const searchInput = document.getElementById("keySearchInput");
  const itemsPerPageSelect = document.getElementById("itemsPerPageSelect");
  const thresholdInput = document.getElementById("failCountThreshold"); // Already used by initializeKeyFilterControls

  if (validKeysListElement) {
    allValidKeys = Array.from(
      validKeysListElement.querySelectorAll("li[data-key]")
    );
    allValidKeys.forEach((li) => {
      const keyTextSpan = li.querySelector(".key-text");
      if (keyTextSpan && keyTextSpan.dataset.fullKey) {
        li.dataset.key = keyTextSpan.dataset.fullKey;
      }
    });
    filteredValidKeys = [...allValidKeys];
  }
  if (invalidKeysListElement) {
    allInvalidKeys = Array.from(
      invalidKeysListElement.querySelectorAll("li[data-key]")
    );
    allInvalidKeys.forEach((li) => {
      const keyTextSpan = li.querySelector(".key-text");
      if (keyTextSpan && keyTextSpan.dataset.fullKey) {
        li.dataset.key = keyTextSpan.dataset.fullKey;
      }
    });
  }

  if (itemsPerPageSelect) {
    itemsPerPage = parseInt(itemsPerPageSelect.value, 10); // Initialize itemsPerPage
    itemsPerPageSelect.addEventListener("change", () => {
      itemsPerPage = parseInt(itemsPerPageSelect.value, 10);
      filterAndSearchValidKeys(); // Re-filter and display page 1 for valid keys
      displayPage("invalid", 1, allInvalidKeys); // Reset invalid keys to page 1
    });
  }

  // Initial display calls
  filterAndSearchValidKeys();
  displayPage("invalid", 1, allInvalidKeys);

  // Event listeners for search and filter (thresholdInput listener is in initializeKeyFilterControls)
  if (searchInput) {
    searchInput.addEventListener("input", filterAndSearchValidKeys);
  }
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("/static/service-worker.js")
        .then((registration) => {
          console.log("ServiceWorker注册成功:", registration.scope);
        })
        .catch((error) => {
          console.log("ServiceWorker注册失败:", error);
        });
    });
  }
}

// 初始化
document.addEventListener("DOMContentLoaded", () => {
  initializePageAnimationsAndEffects();
  initializeSectionToggleListeners();
  initializeKeyFilterControls();
  initializeGlobalBatchVerificationHandlers();
  initializeKeySelectionListeners();
  initializeAutoRefreshControls();
  initializeKeyPaginationAndSearch(); // This will also handle initial display
  registerServiceWorker();

  // Initial batch actions update might be needed if not covered by displayPage
  // updateBatchActions('valid');
  // updateBatchActions('invalid');
});

// --- 新增：删除密钥相关功能 ---

// 新版：显示单个密钥删除确认模态框
function showSingleKeyDeleteConfirmModal(key, button) {
  const modalElement = document.getElementById("singleKeyDeleteConfirmModal");
  const titleElement = document.getElementById(
    "singleKeyDeleteConfirmModalTitle"
  );
  const messageElement = document.getElementById(
    "singleKeyDeleteConfirmModalMessage"
  );
  const confirmButton = document.getElementById("confirmSingleKeyDeleteBtn");

  const keyDisplay =
    key.substring(0, 4) + "..." + key.substring(key.length - 4);
  titleElement.textContent = "确认删除密钥";
  messageElement.innerHTML = `确定要删除密钥 <span class="font-mono text-amber-300 font-semibold">${keyDisplay}</span> 吗？<br>此操作无法撤销。`;

  // 移除旧的监听器并重新附加，以确保 key 和 button 参数是最新的
  const newConfirmButton = confirmButton.cloneNode(true);
  confirmButton.parentNode.replaceChild(newConfirmButton, confirmButton);

  newConfirmButton.onclick = () => executeSingleKeyDelete(key, button);

  modalElement.classList.remove("hidden");
}

// 新版：关闭单个密钥删除确认模态框
function closeSingleKeyDeleteConfirmModal() {
  document
    .getElementById("singleKeyDeleteConfirmModal")
    .classList.add("hidden");
}

// 新版：执行单个密钥删除
async function executeSingleKeyDelete(key, button) {
  closeSingleKeyDeleteConfirmModal();

  button.disabled = true;
  const originalHtml = button.innerHTML;
  // 使用字体图标，确保一致性
  button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>删除中';

  try {
    const response = await fetchAPI(`/api/config/keys/${key}`, {
      method: "DELETE",
    });

    if (response.success) {
      // 使用 resultModal 并确保刷新
      showResultModal(true, response.message || "密钥删除成功", true);
    } else {
      // 使用 resultModal，失败时不刷新，以便用户看到错误信息
      showResultModal(false, response.message || "密钥删除失败", false);
      button.innerHTML = originalHtml;
      button.disabled = false;
    }
  } catch (error) {
    console.error("删除密钥 API 请求失败:", error);
    showResultModal(false, `删除密钥请求失败: ${error.message}`, false);
    button.innerHTML = originalHtml;
    button.disabled = false;
  }
}

// 显示批量删除确认模态框
function showDeleteConfirmationModal(type, event) {
  if (event) {
    event.stopPropagation();
  }
  const modalElement = document.getElementById("deleteConfirmModal");
  const titleElement = document.getElementById("deleteConfirmModalTitle");
  const messageElement = document.getElementById("deleteConfirmModalMessage");
  const confirmButton = document.getElementById("confirmDeleteBtn");

  const selectedKeys = getSelectedKeys(type);
  const count = selectedKeys.length;

  titleElement.textContent = "确认批量删除";
  if (count > 0) {
    messageElement.textContent = `确定要批量删除选中的 ${count} 个${
      type === "valid" ? "有效" : "无效"
    }密钥吗？此操作无法撤销。`;
    confirmButton.disabled = false;
  } else {
    // 此情况理论上不应发生，因为批量删除按钮在未选中时是禁用的
    messageElement.textContent = `请先选择要删除的${
      type === "valid" ? "有效" : "无效"
    }密钥。`;
    confirmButton.disabled = true;
  }

  confirmButton.onclick = () => executeDeleteSelectedKeys(type);
  modalElement.classList.remove("hidden");
}

// 关闭批量删除确认模态框
function closeDeleteConfirmationModal() {
  document.getElementById("deleteConfirmModal").classList.add("hidden");
}

// 执行批量删除
async function executeDeleteSelectedKeys(type) {
  closeDeleteConfirmationModal();

  const selectedKeys = getSelectedKeys(type);
  if (selectedKeys.length === 0) {
    showNotification("没有选中的密钥可删除", "warning");
    return;
  }

  // 找到批量删除按钮并显示加载状态 (假设它在对应类型的 batchActions 中是最后一个按钮)
  const batchActionsDiv = document.getElementById(`${type}BatchActions`);
  const deleteButton = batchActionsDiv
    ? batchActionsDiv.querySelector("button.bg-red-600")
    : null;

  let originalDeleteBtnHtml = "";
  if (deleteButton) {
    originalDeleteBtnHtml = deleteButton.innerHTML;
    deleteButton.disabled = true;
    deleteButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 删除中';
  }

  try {
    const response = await fetchAPI("/api/config/keys/delete-selected", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keys: selectedKeys }),
    });

    if (response.success) {
      // 使用 resultModal 显示更详细的结果
      const message =
        response.message ||
        `成功删除 ${response.deleted_count || selectedKeys.length} 个密钥。`;
      showResultModal(true, message, true); // true 表示成功，message，true 表示关闭后刷新
    } else {
      showResultModal(false, response.message || "批量删除密钥失败", true); // false 表示失败，message，true 表示关闭后刷新
    }
  } catch (error) {
    console.error("批量删除 API 请求失败:", error);
    showResultModal(false, `批量删除请求失败: ${error.message}`, true);
  } finally {
    // resultModal 关闭时会刷新页面，所以通常不需要在这里恢复按钮状态。
    // 如果不刷新，则需要恢复按钮状态：
    // if (deleteButton && (!document.getElementById("resultModal") || document.getElementById("resultModal").classList.contains("hidden") || document.getElementById("resultModalTitle").textContent.includes("失败"))) {
    //   deleteButton.innerHTML = originalDeleteBtnHtml;
    //   // 按钮的 disabled 状态会在 updateBatchActions 中处理，或者因页面刷新而重置
    // }
  }
}

// --- 结束：删除密钥相关功能 ---

function toggleKeyVisibility(button) {
  const keyContainer = button.closest(".flex.items-center.gap-1");
  const keyTextSpan = keyContainer.querySelector(".key-text");
  const eyeIcon = button.querySelector("i");
  const fullKey = keyTextSpan.dataset.fullKey;
  const maskedKey =
    fullKey.substring(0, 4) + "..." + fullKey.substring(fullKey.length - 4);

  if (keyTextSpan.textContent === maskedKey) {
    keyTextSpan.textContent = fullKey;
    eyeIcon.classList.remove("fa-eye");
    eyeIcon.classList.add("fa-eye-slash");
    button.title = "隐藏密钥";
  } else {
    keyTextSpan.textContent = maskedKey;
    eyeIcon.classList.remove("fa-eye-slash");
    eyeIcon.classList.add("fa-eye");
    button.title = "显示密钥";
  }
}

// --- API 调用详情模态框逻辑 ---

// 显示 API 调用详情模态框
async function showApiCallDetails(
  period,
  totalCalls,
  successCalls,
  failureCalls
) {
  const modal = document.getElementById("apiCallDetailsModal");
  const contentArea = document.getElementById("apiCallDetailsContent");
  const titleElement = document.getElementById("apiCallDetailsModalTitle");

  if (!modal || !contentArea || !titleElement) {
    console.error("无法找到 API 调用详情模态框元素");
    showNotification("无法显示详情，页面元素缺失", "error");
    return;
  }

  // 设置标题
  let periodText = "";
  switch (period) {
    case "1m":
      periodText = "最近 1 分钟";
      break;
    case "1h":
      periodText = "最近 1 小时";
      break;
    case "24h":
      periodText = "最近 24 小时";
      break;
    default:
      periodText = "指定时间段";
  }
  titleElement.textContent = `${periodText} API 调用详情`;

  // 显示模态框并设置加载状态
  modal.classList.remove("hidden");
  contentArea.innerHTML = `
        <div class="text-center py-10">
             <i class="fas fa-spinner fa-spin text-primary-600 text-3xl"></i>
             <p class="text-gray-500 mt-2">加载中...</p>
        </div>`;

  try {
    const data = await fetchAPI(`/api/stats/details?period=${period}`);
    if (data) {
      renderApiCallDetails(
        data,
        contentArea,
        totalCalls,
        successCalls,
        failureCalls
      );
    } else {
      renderApiCallDetails(
        [],
        contentArea,
        totalCalls,
        successCalls,
        failureCalls
      ); // Show empty state if no data
    }
  } catch (apiError) {
    console.error("获取 API 调用详情失败:", apiError);
    contentArea.innerHTML = `
            <div class="text-center py-10 text-danger-500">
                <i class="fas fa-exclamation-triangle text-3xl"></i>
                <p class="mt-2">加载失败: ${apiError.message}</p>
            </div>`;
  }
}

// 关闭 API 调用详情模态框
function closeApiCallDetailsModal() {
  const modal = document.getElementById("apiCallDetailsModal");
  if (modal) {
    modal.classList.add("hidden");
  }
}

// 渲染 API 调用详情到模态框
function renderApiCallDetails(
  data,
  container,
  totalCalls,
  successCalls,
  failureCalls
) {
  let summaryHtml = "";
  // 只有在提供了这些统计数据时才显示概览
  if (
    totalCalls !== undefined &&
    successCalls !== undefined &&
    failureCalls !== undefined
  ) {
    summaryHtml = `
        <div class="mb-4 p-3 bg-white dark:bg-gray-700 rounded-lg"> 
            <h4 class="font-semibold text-gray-700 dark:text-gray-200 mb-2 text-md border-b pb-1.5 dark:border-gray-600">期间调用概览:</h4>
            <div class="grid grid-cols-3 gap-2 text-center">
                <div>
                    <p class="text-sm text-gray-500 dark:text-gray-400">总计</p>
                    <p class="text-lg font-bold text-primary-600 dark:text-primary-400">${totalCalls}</p>
                </div>
                <div>
                    <p class="text-sm text-gray-500 dark:text-gray-400">成功</p>
                    <p class="text-lg font-bold text-success-600 dark:text-success-400">${successCalls}</p>
                </div>
                <div>
                    <p class="text-sm text-gray-500 dark:text-gray-400">失败</p>
                    <p class="text-lg font-bold text-danger-600 dark:text-danger-400">${failureCalls}</p>
                </div>
            </div>
        </div>
    `;
  }

  if (!data || data.length === 0) {
    container.innerHTML =
      summaryHtml +
      `
            <div class="text-center py-10 text-gray-500 dark:text-gray-400">
                <i class="fas fa-info-circle text-3xl"></i>
                <p class="mt-2">该时间段内没有 API 调用记录。</p>
            </div>`;
    return;
  }

  // 创建表格
  let tableHtml = `
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700/50">
                <tr>
                    <th scope="col" class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">时间</th>
                    <th scope="col" class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">密钥 (部分)</th>
                    <th scope="col" class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">模型</th>
                    <th scope="col" class="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">状态</th>
                </tr>
            </thead>
            <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
    `;

  // 填充表格行
  data.forEach((call) => {
    const timestamp = new Date(call.timestamp).toLocaleString();
    const keyDisplay = call.key
      ? `${call.key.substring(0, 4)}...${call.key.substring(
          call.key.length - 4
        )}`
      : "N/A";
    const statusClass =
      call.status === "success"
        ? "text-success-600 dark:text-success-400"
        : "text-danger-600 dark:text-danger-400";
    const statusIcon =
      call.status === "success" ? "fa-check-circle" : "fa-times-circle";

    tableHtml += `
            <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">${timestamp}</td>
                <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 font-mono">${keyDisplay}</td>
                <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${
                  call.model || "N/A"
                }</td>
                <td class="px-4 py-2 whitespace-nowrap text-sm ${statusClass}">
                    <i class="fas ${statusIcon} mr-1"></i>
                    ${call.status}
                </td>
            </tr>
        `;
  });

  tableHtml += `
            </tbody>
        </table>
    `;

  container.innerHTML = summaryHtml + tableHtml; // Prepend summary
}

// --- 密钥使用详情模态框逻辑 ---

// 显示密钥使用详情模态框
window.showKeyUsageDetails = async function (key) {
  const modal = document.getElementById("keyUsageDetailsModal");
  const contentArea = document.getElementById("keyUsageDetailsContent");
  const titleElement = document.getElementById("keyUsageDetailsModalTitle");
  const keyDisplay =
    key.substring(0, 4) + "..." + key.substring(key.length - 4);

  if (!modal || !contentArea || !titleElement) {
    console.error("无法找到密钥使用详情模态框元素");
    showNotification("无法显示详情，页面元素缺失", "error");
    return;
  }

  // renderKeyUsageDetails 变为 showKeyUsageDetails 的局部函数
  function renderKeyUsageDetails(data, container) {
    if (!data || Object.keys(data).length === 0) {
      container.innerHTML = `
                <div class="text-center py-10 text-gray-500">
                    <i class="fas fa-info-circle text-3xl"></i>
                    <p class="mt-2">该密钥在最近24小时内没有调用记录。</p>
                </div>`;
      return;
    }
    let tableHtml = `
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">模型名称</th>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">调用次数 (24h)</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">`;
    const sortedModels = Object.entries(data).sort(
      ([, countA], [, countB]) => countB - countA
    );
    sortedModels.forEach(([model, count]) => {
      tableHtml += `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${model}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${count}</td>
                </tr>`;
    });
    tableHtml += `
                </tbody>
            </table>`;
    container.innerHTML = tableHtml;
  }

  // 设置标题
  titleElement.textContent = `密钥 ${keyDisplay} - 最近24小时请求详情`;

  // 显示模态框并设置加载状态
  modal.classList.remove("hidden");
  contentArea.innerHTML = `
        <div class="text-center py-10">
             <i class="fas fa-spinner fa-spin text-primary-600 text-3xl"></i>
             <p class="text-gray-500 mt-2">加载中...</p>
        </div>`;

  try {
    const data = await fetchAPI(`/api/key-usage-details/${key}`);
    if (data) {
      renderKeyUsageDetails(data, contentArea);
    } else {
      renderKeyUsageDetails({}, contentArea); // Show empty state if no data
    }
  } catch (apiError) {
    console.error("获取密钥使用详情失败:", apiError);
    contentArea.innerHTML = `
            <div class="text-center py-10 text-danger-500">
                <i class="fas fa-exclamation-triangle text-3xl"></i>
                <p class="mt-2">加载失败: ${apiError.message}</p>
            </div>`;
  }
};

// 关闭密钥使用详情模态框
window.closeKeyUsageDetailsModal = function () {
  const modal = document.getElementById("keyUsageDetailsModal");
  if (modal) {
    modal.classList.add("hidden");
  }
};

// window.renderKeyUsageDetails 函数已被移入 showKeyUsageDetails 内部, 此处残留代码已删除。

// --- Key List Display & Pagination ---

/**
 * Displays key list items for a specific type and page.
 * @param {string} type 'valid' or 'invalid'
 * @param {number} page Page number (1-based)
 * @param {Array} keyItemsArray The array of li elements to paginate (e.g., filteredValidKeys, allInvalidKeys)
 */
function displayPage(type, page, keyItemsArray) {
  const listElement = document.getElementById(`${type}Keys`);
  const paginationControls = document.getElementById(
    `${type}PaginationControls`
  );
  if (!listElement || !paginationControls) return;

  // Update current page based on type
  if (type === "valid") {
    validCurrentPage = page;
    // Read itemsPerPage from the select specifically for valid keys
    const itemsPerPageSelect = document.getElementById("itemsPerPageSelect");
    itemsPerPage = itemsPerPageSelect
      ? parseInt(itemsPerPageSelect.value, 10)
      : 10;
  } else {
    invalidCurrentPage = page;
    // For invalid keys, use a fixed itemsPerPage or the same global one
    // itemsPerPage = 10; // Or read from a different select if needed
  }

  const totalItems = keyItemsArray.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  page = Math.max(1, Math.min(page, totalPages || 1)); // Ensure page is valid

  // Update current page variable again after validation
  if (type === "valid") {
    validCurrentPage = page;
  } else {
    invalidCurrentPage = page;
  }

  const startIndex = (page - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;

  listElement.innerHTML = ""; // Clear current list content

  const pageItems = keyItemsArray.slice(startIndex, endIndex);

  if (pageItems.length > 0) {
    pageItems.forEach((originalMasterItem) => {
      const listItemClone = originalMasterItem.cloneNode(true);
      // The checkbox's 'checked' state is cloned from the master item.
      // Now, ensure the 'selected' class on the clone matches this cloned checkbox state.
      const checkboxInClone = listItemClone.querySelector(".key-checkbox");
      if (checkboxInClone) {
        listItemClone.classList.toggle("selected", checkboxInClone.checked);
      }
      listElement.appendChild(listItemClone);
    });
  } else if (
    totalItems === 0 &&
    type === "valid" &&
    (document.getElementById("failCountThreshold").value !== "0" ||
      document.getElementById("keySearchInput").value !== "")
  ) {
    // Handle empty state after filtering/searching for valid keys
    const noMatchMsgId = "no-valid-keys-msg";
    let noMatchMsg = listElement.querySelector(`#${noMatchMsgId}`);
    if (!noMatchMsg) {
      noMatchMsg = document.createElement("li");
      noMatchMsg.id = noMatchMsgId;
      noMatchMsg.className = "text-center text-gray-500 py-4 col-span-full";
      noMatchMsg.textContent = "没有符合条件的有效密钥";
      listElement.appendChild(noMatchMsg);
    }
    noMatchMsg.style.display = "";
  } else if (totalItems === 0) {
    // Handle empty state for initially empty lists
    const emptyMsg = document.createElement("li");
    emptyMsg.className = "text-center text-gray-500 py-4 col-span-full";
    emptyMsg.textContent = `暂无${type === "valid" ? "有效" : "无效"}密钥`;
    listElement.appendChild(emptyMsg);
  }

  setupPaginationControls(type, page, totalPages, keyItemsArray);
  updateBatchActions(type); // Update batch actions based on the currently displayed page
  // Re-attach event listeners for buttons inside the newly added list items if needed (using event delegation is better)
}

/**
 * Sets up pagination controls.
 * @param {string} type 'valid' or 'invalid'
 * @param {number} currentPage Current page number
 * @param {number} totalPages Total number of pages
 * @param {Array} keyItemsArray The array of li elements being paginated
 */
function setupPaginationControls(type, currentPage, totalPages, keyItemsArray) {
  const controlsContainer = document.getElementById(
    `${type}PaginationControls`
  );
  if (!controlsContainer) return;

  controlsContainer.innerHTML = "";

  if (totalPages <= 1) {
    return; // No controls needed for single/no page
  }

  // Base classes for all buttons (Tailwind for layout, custom for consistent styling)
  const baseButtonClasses =
    "pagination-button px-3 py-1 rounded text-sm transition-colors duration-150 ease-in-out";
  // Define hover classes that work with the custom background by adjusting opacity or a border effect.
  // Since .pagination-button defines a background, a hover effect might be a subtle border change or brightness.
  // For simplicity, we can rely on CSS for hover effects on .pagination-button:hover
  // const hoverClasses = "hover:border-purple-400"; // Example if you want JS to add specific hover behavior

  // Previous Button
  const prevButton = document.createElement("button");
  prevButton.innerHTML = '<i class="fas fa-chevron-left"></i>';
  prevButton.className = `${baseButtonClasses} disabled:opacity-50 disabled:cursor-not-allowed`;
  prevButton.disabled = currentPage === 1;
  prevButton.onclick = () => displayPage(type, currentPage - 1, keyItemsArray);
  controlsContainer.appendChild(prevButton);

  // Page Number Buttons (Logic for ellipsis)
  const maxPageButtons = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxPageButtons / 2));
  let endPage = Math.min(totalPages, startPage + maxPageButtons - 1);

  if (endPage - startPage + 1 < maxPageButtons) {
    startPage = Math.max(1, endPage - maxPageButtons + 1);
  }

  // First Page Button & Ellipsis
  if (startPage > 1) {
    const firstPageButton = document.createElement("button");
    firstPageButton.textContent = "1";
    firstPageButton.className = `${baseButtonClasses}`;
    firstPageButton.onclick = () => displayPage(type, 1, keyItemsArray);
    controlsContainer.appendChild(firstPageButton);
    if (startPage > 2) {
      const ellipsis = document.createElement("span");
      ellipsis.textContent = "...";
      ellipsis.className = "px-3 py-1 text-gray-300 text-sm"; // Adjusted color for dark theme
      controlsContainer.appendChild(ellipsis);
    }
  }

  // Middle Page Buttons
  for (let i = startPage; i <= endPage; i++) {
    const pageButton = document.createElement("button");
    pageButton.textContent = i;
    pageButton.className = `${baseButtonClasses} ${
      i === currentPage
        ? "active font-semibold" // Relies on .pagination-button.active CSS for styling
        : "" // Non-active buttons just use .pagination-button style
    }`;
    pageButton.onclick = () => displayPage(type, i, keyItemsArray);
    controlsContainer.appendChild(pageButton);
  }

  // Ellipsis & Last Page Button
  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      const ellipsis = document.createElement("span");
      ellipsis.textContent = "...";
      ellipsis.className = "px-3 py-1 text-gray-300 text-sm"; // Adjusted color
      controlsContainer.appendChild(ellipsis);
    }
    const lastPageButton = document.createElement("button");
    lastPageButton.textContent = totalPages;
    lastPageButton.className = `${baseButtonClasses}`;
    lastPageButton.onclick = () => displayPage(type, totalPages, keyItemsArray);
    controlsContainer.appendChild(lastPageButton);
  }

  // Next Button
  const nextButton = document.createElement("button");
  nextButton.innerHTML = '<i class="fas fa-chevron-right"></i>';
  nextButton.className = `${baseButtonClasses} disabled:opacity-50 disabled:cursor-not-allowed`;
  nextButton.disabled = currentPage === totalPages;
  nextButton.onclick = () => displayPage(type, currentPage + 1, keyItemsArray);
  controlsContainer.appendChild(nextButton);
}

// --- Filtering & Searching (Valid Keys Only) ---

/**
 * Filters and searches the valid keys based on threshold and search term.
 * Updates the `filteredValidKeys` array and redisplays the first page.
 */
function filterAndSearchValidKeys() {
  const thresholdInput = document.getElementById("failCountThreshold");
  const searchInput = document.getElementById("keySearchInput");

  const threshold = parseInt(thresholdInput.value, 10);
  const filterThreshold = isNaN(threshold) || threshold < 0 ? 0 : threshold;
  const searchTerm = searchInput.value.trim().toLowerCase();

  // Filter from the original full list (allValidKeys)
  filteredValidKeys = allValidKeys.filter((item) => {
    const failCount = parseInt(item.dataset.failCount, 10);
    const fullKey = item.dataset.key || ""; // Use data-key which should hold the full key

    const failCountMatch = failCount >= filterThreshold;
    const searchMatch =
      searchTerm === "" || fullKey.toLowerCase().includes(searchTerm);

    return failCountMatch && searchMatch;
  });

  // Reset to the first page after filtering/searching
  validCurrentPage = 1;
  displayPage("valid", validCurrentPage, filteredValidKeys);
}
