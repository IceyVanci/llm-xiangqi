/**
 * 音效管理器
 * 
 * 功能:
 * - 音效播放管理
 * - 音量控制
 * - 静音控制
 */

// 音效配置
const SOUND_CONFIG = {
  move: { file: 'move.mp3', volume: 0.5 },
  capture: { file: 'capture.mp3', volume: 0.7 },
  check: { file: 'check.mp3', volume: 0.8 },
  gameOver: { file: 'game_over.mp3', volume: 0.6 }
};

class SoundManager {
  constructor() {
    this.audioContext = null;
    this.sounds = {};
    this.enabled = true;
    this.volume = 0.5;
    this.buffers = {};
    this.initialized = false;
  }

  /**
   * 初始化音效系统
   */
  init() {
    if (this.initialized) return;
    
    try {
      // 创建 AudioContext
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContext();
      
      // 创建主音量控制器
      this.gainNode = this.audioContext.createGain();
      this.gainNode.gain.value = this.volume;
      this.gainNode.connect(this.audioContext.destination);
      
      // 预加载音效（使用 Web Audio API 生成简单音效）
      this._generateSounds();
      
      this.initialized = true;
      console.info('[Sound] Initialized');
    } catch (e) {
      console.warn('[Sound] Failed to initialize:', e);
    }
  }

  /**
   * 生成简单音效（代替实际音频文件）
   * 使用 Web Audio API 的 OscillatorNode 生成
   */
  _generateSounds() {
    // move - 短促的提示音
    this._createTone('move', 440, 0.1, 'sine');
    
    // capture - 较低沉的声音
    this._createTone('capture', 220, 0.15, 'triangle');
    
    // check - 警报音
    this._createTone('check', 660, 0.3, 'square');
    
    // gameOver - 结束音
    this._createTone('gameOver', 330, 0.5, 'sine');
  }

  /**
   * 创建音调
   */
  _createTone(name, frequency, duration, type) {
    // 预生成音频数据
    const sampleRate = this.audioContext.sampleRate;
    const numSamples = sampleRate * duration;
    const buffer = this.audioContext.createBuffer(1, numSamples, sampleRate);
    const data = buffer.getChannelData(0);
    
    for (let i = 0; i < numSamples; i++) {
      const t = i / sampleRate;
      let sample = 0;
      
      switch (type) {
        case 'sine':
          sample = Math.sin(2 * Math.PI * frequency * t);
          break;
        case 'square':
          sample = Math.sin(2 * Math.PI * frequency * t) > 0 ? 0.5 : -0.5;
          break;
        case 'triangle':
          sample = 2 * Math.abs(2 * (t * frequency - Math.floor(t * frequency + 0.5))) - 1;
          break;
        default:
          sample = Math.sin(2 * Math.PI * frequency * t);
      }
      
      // 包络（淡入淡出）
      const attack = 0.01;
      const decay = duration * 0.3;
      const sustain = 0.5;
      const release = duration * 0.5;
      
      let envelope = 1;
      if (t < attack) {
        envelope = t / attack;
      } else if (t < attack + decay) {
        envelope = 1 - (1 - sustain) * (t - attack) / decay;
      } else if (t < duration - release) {
        envelope = sustain;
      } else {
        envelope = sustain * (1 - (t - (duration - release)) / release);
      }
      
      data[i] = sample * envelope * 0.3; // 降低整体音量
    }
    
    this.buffers[name] = buffer;
  }

  /**
   * 播放音效
   */
  play(name) {
    if (!this.enabled || !this.initialized || !this.buffers[name]) {
      return;
    }
    
    try {
      // 恢复 AudioContext（如果被暂停）
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume();
      }
      
      // 创建源节点
      const source = this.audioContext.createBufferSource();
      source.buffer = this.buffers[name];
      
      // 创建增益节点控制单个音效音量
      const gainNode = this.audioContext.createGain();
      gainNode.gain.value = SOUND_CONFIG[name]?.volume || 0.5;
      
      // 连接节点
      source.connect(gainNode);
      gainNode.connect(this.gainNode);
      
      // 播放
      source.start(0);
    } catch (e) {
      console.warn('[Sound] Play failed:', e);
    }
  }

  /**
   * 播放移动音效
   */
  playMove() {
    this.play('move');
  }

  /**
   * 播放吃子音效
   */
  playCapture() {
    this.play('capture');
  }

  /**
   * 播放将军音效
   */
  playCheck() {
    this.play('check');
  }

  /**
   * 播放游戏结束音效
   */
  playGameOver() {
    this.play('gameOver');
  }

  /**
   * 设置音量
   */
  setVolume(volume) {
    this.volume = Math.max(0, Math.min(1, volume));
    if (this.gainNode) {
      this.gainNode.gain.value = this.volume;
    }
  }

  /**
   * 获取音量
   */
  getVolume() {
    return this.volume;
  }

  /**
   * 设置是否启用音效
   */
  setEnabled(enabled) {
    this.enabled = enabled;
  }

  /**
   * 获取是否启用音效
   */
  isEnabled() {
    return this.enabled;
  }

  /**
   * 切换音效开关
   */
  toggle() {
    this.enabled = !this.enabled;
    return this.enabled;
  }

  /**
   * 销毁
   */
  dispose() {
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.buffers = {};
    this.initialized = false;
  }
}

// 导出到全局
window.SoundManager = SoundManager;
window.SOUND_CONFIG = SOUND_CONFIG;
