/**
 * 浏览器兼容性检测
 * 
 * 功能:
 * - 检测 WebGL 2.0 支持
 * - 检测浏览器版本
 * - 显示错误页面
 */

class CompatibilityChecker {
  /**
   * 检查浏览器兼容性
   */
  static check() {
    const errors = [];
    const warnings = [];
    
    // 检查 WebGL 2.0 支持
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2');
    if (!gl) {
      errors.push('您的浏览器不支持 WebGL 2.0，请升级到最新版本的 Chrome、Edge 或 Firefox。');
    }
    
    // 检查是否是支持的浏览器
    const browserInfo = CompatibilityChecker.getBrowserInfo();
    if (!CompatibilityChecker.isSupportedBrowser()) {
      warnings.push(`浏览器 ${browserInfo.name} ${browserInfo.version} 可能不完全支持本应用，建议使用 Chrome 113+、Edge 113+ 或 Firefox 141+。`);
    }
    
    // 检查是否有 requestAnimationFrame
    if (typeof requestAnimationFrame === 'undefined') {
      errors.push('您的浏览器不支持 requestAnimationFrame，请升级浏览器。');
    }
    
    // 检查是否有 WebSocket
    if (typeof WebSocket === 'undefined') {
      errors.push('您的浏览器不支持 WebSocket，请升级浏览器。');
    }
    
    return {
      supported: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * 获取浏览器信息
   */
  static getBrowserInfo() {
    const ua = navigator.userAgent;
    let name = 'Unknown';
    let version = '0';
    
    if (ua.indexOf('Chrome') > -1) {
      name = 'Chrome';
      version = ua.match(/Chrome\/(\d+\.\d+)/)?.[1] || '0';
    } else if (ua.indexOf('Firefox') > -1) {
      name = 'Firefox';
      version = ua.match(/Firefox\/(\d+\.\d+)/)?.[1] || '0';
    } else if (ua.indexOf('Safari') > -1 && ua.indexOf('Chrome') === -1) {
      name = 'Safari';
      version = ua.match(/Version\/(\d+\.\d+)/)?.[1] || '0';
    } else if (ua.indexOf('Edge') > -1) {
      name = 'Edge';
      version = ua.match(/Edge\/(\d+\.\d+)/)?.[1] || '0';
    } else if (ua.indexOf('MSIE') > -1 || ua.indexOf('Trident') > -1) {
      name = 'IE';
      version = ua.match(/(?:MSIE |rv:)(\d+\.\d+)/)?.[1] || '0';
    }
    
    return { name, version };
  }

  /**
   * 是否是支持的浏览器
   */
  static isSupportedBrowser() {
    const info = CompatibilityChecker.getBrowserInfo();
    
    switch (info.name) {
      case 'Chrome':
        return parseFloat(info.version) >= 113;
      case 'Edge':
        return parseFloat(info.version) >= 113;
      case 'Firefox':
        return parseFloat(info.version) >= 141;
      case 'Safari':
        return parseFloat(info.version) >= 26;
      default:
        return false;
    }
  }

  /**
   * 显示错误页面
   */
  static showErrorPage(errors) {
    const html = `
      <!DOCTYPE html>
      <html lang="zh-CN">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>浏览器不支持 - LLM-Xiangqi</title>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body {
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            padding: 20px;
          }
          .error-container {
            max-width: 500px;
            text-align: center;
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 40px;
            border: 1px solid rgba(255,255,255,0.1);
          }
          h1 {
            font-size: 2em;
            margin-bottom: 20px;
            color: #e74c3c;
          }
          .error-icon {
            font-size: 4em;
            margin-bottom: 20px;
          }
          .error-list {
            text-align: left;
            margin: 20px 0;
            padding: 20px;
            background: rgba(231, 76, 60, 0.1);
            border-radius: 8px;
            border-left: 4px solid #e74c3c;
          }
          .error-list li {
            margin: 10px 0;
            line-height: 1.6;
          }
          .btn {
            display: inline-block;
            margin-top: 20px;
            padding: 12px 30px;
            background: #3498db;
            color: #fff;
            border-radius: 8px;
            text-decoration: none;
            cursor: pointer;
          }
          .btn:hover {
            background: #2980b9;
          }
        </style>
      </head>
      <body>
        <div class="error-container">
          <div class="error-icon">⚠️</div>
          <h1>浏览器不支持</h1>
          <div class="error-list">
            <ul>
              ${errors.map(e => `<li>${e}</li>`).join('')}
            </ul>
          </div>
          <p>请升级您的浏览器到最新版本后重试。</p>
          <a href="https://www.google.com/chrome/" class="btn" target="_blank">下载 Chrome</a>
          <br><br>
          <a href="javascript:location.reload()" class="btn">重新检查</a>
        </div>
      </body>
      </html>
    `;
    
    document.open();
    document.write(html);
    document.close();
  }
}

// 导出到全局
window.CompatibilityChecker = CompatibilityChecker;
