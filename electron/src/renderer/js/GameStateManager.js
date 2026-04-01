/**
 * 游戏状态管理器
 * 
 * 功能:
 * - 管理游戏状态
 * - 解析 FEN
 * - 走步历史
 * - 坐标转换（FEN <-> 3D）
 * - FEN 验证
 */

// 游戏状态枚举
const GAME_STATUS = {
  NOT_STARTED: 'not_started',
  PLAYING: 'playing',
  FINISHED: 'finished'
};

// 游戏阶段枚举
const GAME_PHASE = {
  NOT_STARTED: 'not_started',
  RED_TO_MOVE: 'red_to_move',
  BLACK_TO_MOVE: 'black_to_move',
  GAME_OVER: 'game_over'
};

// 游戏结果枚举
const GAME_RESULT = {
  RED_WIN: 'red_win',
  BLACK_WIN: 'black_win',
  DRAW: 'draw',
  IN_PROGRESS: 'in_progress'
};

// 游戏结束原因枚举
const GAME_END_REASON = {
  // 红方胜利
  RED_CHECKMATE: 'red_checkmate',
  RED_STALEMATE: 'red_stalemate',
  RED_KING_CAPTURED: 'red_king_captured',
  RED_RESIGNATION: 'red_resignation',
  
  // 黑方胜利
  BLACK_CHECKMATE: 'black_checkmate',
  BLACK_STALEMATE: 'black_stalemate',
  BLACK_KING_CAPTURED: 'black_king_captured',
  BLACK_RESIGNATION: 'black_resignation',
  
  // 和棋
  THREE_FOLD_REPETITION: 'three_fold_repetition',
  MAX_TURNS: 'max_turns',
  STALEMATE_DRAW: 'stalemate_draw',
  
  // 违规
  RED_PERPETUAL_CHECK: 'red_perpetual_check',
  BLACK_PERPETUAL_CHECK: 'black_perpetual_check',
  
  // 未开始/进行中
  NOT_STARTED: 'not_started',
  IN_PROGRESS: 'in_progress'
};

// 棋子名称映射
const PIECE_NAMES = {
  'K': '帅', 'k': '将',
  'A': '仕', 'a': '士',
  'B': '相', 'b': '象',
  'N': '马', 'n': '马',
  'R': '车', 'r': '车',
  'C': '炮', 'c': '炮',
  'P': '兵', 'p': '卒',
};

// FEN验证正则表达式
const FEN_PATTERN = /^[rnbakabnrpcRNBAKABNRPC1-9\/]+ [wb](?: - - \d+ \d+)?$/;

// 最大FEN长度（安全限制）
const MAX_FEN_LENGTH = 200;

class GameStateManager {
  constructor() {
    this.status = GAME_STATUS.NOT_STARTED;
    this.phase = GAME_PHASE.NOT_STARTED;
    this.turn = 'Red';
    this.turnNumber = 0;
    this.fen = '';
    this.players = {
      Red: { name: '红方', model: '' },
      Black: { name: '黑方', model: '' }
    };
    this.moveHistory = [];
    this.lastMove = null;
    this.result = null;
    this.resultReason = null;
    this.endReason = null;
    this.listeners = [];
    
    // 位置计数器（用于快速检测重复局面）
    this._positionCounter = {};
  }

  /**
   * 添加状态变化监听器
   */
  addListener(callback) {
    this.listeners.push(callback);
  }

  /**
   * 触发状态变化
   */
  _notifyListeners(type, data) {
    this.listeners.forEach(callback => {
      try {
        callback(type, data);
      } catch (e) {
        console.error('[GameStateManager] Listener error:', e);
      }
    });
  }

  /**
   * 验证FEN格式
   * @param {string} fen - FEN字符串
   * @returns {object} - { valid: boolean, error: string | null }
   */
  validateFen(fen) {
    if (typeof fen !== 'string') {
      return { valid: false, error: 'FEN must be a string' };
    }
    
    if (!fen || !fen.trim()) {
      return { valid: false, error: 'FEN cannot be empty' };
    }
    
    if (fen.length > MAX_FEN_LENGTH) {
      return { valid: false, error: `FEN too long (max ${MAX_FEN_LENGTH} chars)` };
    }
    
    if (!FEN_PATTERN.test(fen)) {
      return { valid: false, error: 'Invalid FEN format' };
    }
    
    // 验证行数
    const boardPart = fen.split(' ')[0];
    const rows = boardPart.split('/');
    if (rows.length !== 10) {
      return { valid: false, error: `FEN must have 10 rows, got ${rows.length}` };
    }
    
    // 验证每行列数
    for (let i = 0; i < rows.length; i++) {
      let colCount = 0;
      for (const char of rows[i]) {
        if (char >= '1' && char <= '9') {
          colCount += parseInt(char);
        } else if (/[rnbakabnrpcRNBAKABNRPC]/.test(char)) {
          colCount += 1;
        } else {
          return { valid: false, error: `Invalid character '${char}' in row ${i}` };
        }
      }
      if (colCount !== 9) {
        return { valid: false, error: `Row ${i} must have 9 columns, got ${colCount}` };
      }
    }
    
    return { valid: true, error: null };
  }

  /**
   * 从服务器初始化状态
   */
  initFromServer(state) {
    // 验证并设置FEN
    if (state.fen) {
      const validation = this.validateFen(state.fen);
      if (validation.valid) {
        this.fen = state.fen;
      } else {
        console.warn('[GameStateManager] Invalid FEN from server:', validation.error);
        this.fen = '';
      }
    } else {
      this.fen = '';
    }
    
    // 设置阶段
    if (state.phase) {
      this.phase = state.phase;
    } else if (state.status === 'finished') {
      this.phase = GAME_PHASE.GAME_OVER;
    } else {
      this.phase = GAME_PHASE.RED_TO_MOVE;
    }
    
    // 设置回合
    this.turn = state.turn || 'Red';
    this.turnNumber = state.turn_number || state.turnCount || 1;
    
    // 设置状态
    if (state.status === 'finished' || this.phase === GAME_PHASE.GAME_OVER) {
      this.status = GAME_STATUS.FINISHED;
    } else if (this.fen) {
      this.status = GAME_STATUS.PLAYING;
    } else {
      this.status = GAME_STATUS.NOT_STARTED;
    }
    
    if (state.players) {
      this.players.Red = state.players.Red || { name: '红方', model: '' };
      this.players.Black = state.players.Black || { name: '黑方', model: '' };
    }
    
    if (state.game_history) {
      this.moveHistory = state.game_history;
    } else if (state.move_history) {
      this.moveHistory = state.move_history;
    }
    
    if (state.last_move) {
      this.lastMove = state.last_move;
    }
    
    // 设置结果
    if (state.result) {
      this.result = state.result;
      this.resultReason = state.result_reason || '';
      
      // 设置 end_reason
      if (state.end_reason) {
        this.endReason = state.end_reason;
      } else {
        this.endReason = this._inferEndReason(state.result_reason);
      }
    } else {
      this.result = null;
      this.resultReason = null;
      this.endReason = null;
    }
    
    // 初始化位置计数器
    this._initPositionCounter();
    
    this._notifyListeners('init', state);
  }

  /**
   * 从结果字符串推断 end_reason
   */
  _inferEndReason(reason) {
    if (!reason) return GAME_END_REASON.IN_PROGRESS;
    
    const reasonLower = reason.toLowerCase();
    
    // 红方胜利相关
    if (reason.includes('红方被将死')) return GAME_END_REASON.RED_CHECKMATE;
    if (reason.includes('红方被困')) return GAME_END_REASON.RED_STALEMATE;
    if (reason.includes('红帅被吃') || reason.includes('红将被吃')) return GAME_END_REASON.BLACK_KING_CAPTURED;
    if (reasonLower.includes('red resigned')) return GAME_END_REASON.RED_RESIGNATION;
    
    // 黑方胜利相关
    if (reason.includes('黑方被将死')) return GAME_END_REASON.BLACK_CHECKMATE;
    if (reason.includes('黑方被困')) return GAME_END_REASON.BLACK_STALEMATE;
    if (reason.includes('黑将被吃') || reason.includes('黑帅被吃')) return GAME_END_REASON.RED_KING_CAPTURED;
    if (reasonLower.includes('black resigned')) return GAME_END_REASON.BLACK_RESIGNATION;
    
    // 和棋相关
    if (reason.includes('三次重复局面')) return GAME_END_REASON.THREE_FOLD_REPETITION;
    if (reasonLower.includes('maximum turns')) return GAME_END_REASON.MAX_TURNS;
    if (reason.includes('判和')) return GAME_END_REASON.STALEMATE_DRAW;
    
    // 长将违规
    if (reason.includes('红方长将')) return GAME_END_REASON.RED_PERPETUAL_CHECK;
    if (reason.includes('黑方长将')) return GAME_END_REASON.BLACK_PERPETUAL_CHECK;
    
    return GAME_END_REASON.STALEMATE_DRAW;
  }

  /**
   * 获取 end_reason 的中文显示
   */
  getEndReasonDisplay() {
    const displayMap = {
      [GAME_END_REASON.RED_CHECKMATE]: '红方胜利 - 将军！',
      [GAME_END_REASON.RED_STALEMATE]: '红方胜利 - 黑方被困毙',
      [GAME_END_REASON.RED_KING_CAPTURED]: '红方胜利 - 吃掉黑将',
      [GAME_END_REASON.RED_RESIGNATION]: '红方胜利 - 黑方投降',
      [GAME_END_REASON.BLACK_CHECKMATE]: '黑方胜利 - 将军！',
      [GAME_END_REASON.BLACK_STALEMATE]: '黑方胜利 - 红方被困毙',
      [GAME_END_REASON.BLACK_KING_CAPTURED]: '黑方胜利 - 吃掉红帅',
      [GAME_END_REASON.BLACK_RESIGNATION]: '黑方胜利 - 红方投降',
      [GAME_END_REASON.THREE_FOLD_REPETITION]: '和棋 - 三次重复局面',
      [GAME_END_REASON.MAX_TURNS]: '和棋 - 达到最大回合数',
      [GAME_END_REASON.STALEMATE_DRAW]: '和棋',
      [GAME_END_REASON.RED_PERPETUAL_CHECK]: '红方胜利 - 黑方长将违规',
      [GAME_END_REASON.BLACK_PERPETUAL_CHECK]: '黑方胜利 - 红方长将违规',
      [GAME_END_REASON.NOT_STARTED]: '游戏未开始',
      [GAME_END_REASON.IN_PROGRESS]: '游戏进行中',
    };
    return displayMap[this.endReason] || '未知结果';
  }

  /**
   * 初始化位置计数器
   */
  _initPositionCounter() {
    this._positionCounter = {};
    // 统计每个局面的出现次数
    for (const fen of this.moveHistory) {
      const boardKey = fen.split(' ')[0];
      this._positionCounter[boardKey] = (this._positionCounter[boardKey] || 0) + 1;
    }
  }

  /**
   * 处理走步
   */
  handleMove(moveData) {
    // 验证并更新FEN
    if (moveData.fen_after) {
      const validation = this.validateFen(moveData.fen_after);
      if (validation.valid) {
        this.fen = moveData.fen_after;
        
        // 更新位置计数器
        const boardKey = this.fen.split(' ')[0];
        this._positionCounter[boardKey] = (this._positionCounter[boardKey] || 0) + 1;
      }
    } else if (moveData.fen) {
      const validation = this.validateFen(moveData.fen);
      if (validation.valid) {
        this.fen = moveData.fen;
      }
    }
    
    this.turnNumber++;
    
    // 更新回合
    if (this.phase === GAME_PHASE.RED_TO_MOVE) {
      this.phase = GAME_PHASE.BLACK_TO_MOVE;
      this.turn = 'Black';
    } else if (this.phase === GAME_PHASE.BLACK_TO_MOVE) {
      this.phase = GAME_PHASE.RED_TO_MOVE;
      this.turn = 'Red';
    }
    
    this.status = GAME_STATUS.PLAYING;
    
    // 更新走步历史
    if (moveData.move) {
      this.moveHistory.push(moveData.move);
    }
    
    this.lastMove = {
      from: moveData.from_pos || (moveData.move ? moveData.move.substring(0, 2) : null),
      to: moveData.to_pos || (moveData.move ? moveData.move.substring(2, 4) : null),
      piece: moveData.piece,
      captured: moveData.captured
    };
    
    this._notifyListeners('move', moveData);
  }

  /**
   * 处理游戏结束
   */
  handleGameOver(gameOverData) {
    this.status = GAME_STATUS.FINISHED;
    this.phase = GAME_PHASE.GAME_OVER;
    
    this.result = gameOverData.result;
    this.resultReason = gameOverData.result_reason || '';
    
    // 设置 end_reason
    if (gameOverData.end_reason) {
      this.endReason = gameOverData.end_reason;
    } else {
      this.endReason = this._inferEndReason(gameOverData.result_reason);
    }
    
    if (gameOverData.move_history || gameOverData.game_history) {
      this.moveHistory = gameOverData.move_history || gameOverData.game_history;
      this._initPositionCounter();
    }
    
    this._notifyListeners('game_over', gameOverData);
  }

  // ==================== 坐标转换功能 ====================

  /**
   * 将FEN坐标 (col, row) 转换为3D坐标
   * @param {number} col - 列 (0-8)
   * @param {number} row - 行 (0-9)
   * @returns {object} - { x, y, z } 3D坐标
   */
  fenTo3D(col, row) {
    // 棋盘是10行 x 9列
    // 红方在下方（row 0-4），黑方在上方（row 5-9）
    // 
    // 3D坐标系：
    // - X轴：列方向，范围 [-4, 4]
    // - Y轴：高度（固定为棋子高度）
    // - Z轴：行方向，范围 [-4.5, 4.5]
    // 
    // 转换公式：
    // - x = col - 4 (列 0 -> -4, 列 8 -> 4)
    // - z = row - 4.5 (行 0 -> -4.5, 行 9 -> 4.5)
    
    const x = col - 4;
    const z = row - 4.5;
    const y = 0; // 高度，稍后根据棋子类型调整
    
    return { x, y, z };
  }

  /**
   * 将ICCS坐标字符串转换为3D坐标
   * @param {string} iccs - ICCS坐标字符串 (如 'h2')
   * @returns {object} - { x, y, z } 3D坐标
   */
  iccsTo3D(iccs) {
    if (!iccs || iccs.length !== 2) {
      return null;
    }
    
    const col = iccs.charCodeAt(0) - 97; // 'a' -> 0, 'i' -> 8
    const row = parseInt(iccs[1]); // '0' -> 0, '9' -> 9
    
    if (col < 0 || col > 8 || row < 0 || row > 9) {
      return null;
    }
    
    return this.fenTo3D(col, row);
  }

  /**
   * 将3D坐标转换为FEN坐标
   * @param {number} x - X坐标
   * @param {number} z - Z坐标
   * @returns {object} - { col, row } FEN坐标
   */
  _3DToFen(x, z) {
    const col = Math.round(x + 4);
    const row = Math.round(z + 4.5);
    
    if (col < 0 || col > 8 || row < 0 || row > 9) {
      return null;
    }
    
    return { col, row };
  }

  /**
   * 将3D坐标转换为ICCS坐标
   * @param {number} x - X坐标
   * @param {number} z - Z坐标
   * @returns {string} - ICCS坐标字符串 (如 'h2')
   */
  _3DToIccs(x, z) {
    const pos = this._3DToFen(x, z);
    if (!pos) {
      return null;
    }
    
    const colChar = String.fromCharCode(97 + pos.col);
    return colChar + pos.row;
  }

  // ==================== 棋盘布局功能 ====================

  /**
   * 获取棋盘布局（棋子位置）
   */
  getBoardLayout() {
    if (!this.fen) return [];
    
    const layout = [];
    const parts = this.fen.split(' ');
    const rows = parts[0].split('/');
    
    for (let r = 9; r >= 0; r--) {
      let col = 0;
      const rowStr = rows[9 - r];
      
      for (const char of rowStr) {
        if (char >= '1' && char <= '9') {
          col += parseInt(char);
        } else {
          const iccs = String.fromCharCode(97 + col) + r;
          layout.push({
            position: iccs,
            col: col,
            row: r,
            piece: char,
            pieceName: PIECE_NAMES[char] || char,
            isRed: char === char.toUpperCase(),
            // 3D坐标
            ...this.fenTo3D(col, r)
          });
          col++;
        }
      }
    }
    
    return layout;
  }

  /**
   * 获取棋盘布局（带3D坐标）
   */
  getBoardLayoutWith3D() {
    return this.getBoardLayout();
  }

  /**
   * 根据3D坐标获取棋子
   * @param {number} x - X坐标
   * @param {number} z - Z坐标
   * @returns {object|null} - 棋子信息或null
   */
  getPieceAt3D(x, z) {
    const pos = this._3DToFen(x, z);
    if (!pos) {
      return null;
    }
    
    const layout = this.getBoardLayout();
    return layout.find(p => p.col === pos.col && p.row === pos.row) || null;
  }

  /**
   * 根据ICCS坐标获取棋子
   * @param {string} iccs - ICCS坐标
   * @returns {object|null} - 棋子信息或null
   */
  getPieceAtIccs(iccs) {
    if (!iccs || iccs.length !== 2) {
      return null;
    }
    
    const col = iccs.charCodeAt(0) - 97;
    const row = parseInt(iccs[1]);
    
    const layout = this.getBoardLayout();
    return layout.find(p => p.col === col && p.row === row) || null;
  }

  // ==================== 显示功能 ====================

  /**
   * 获取回合显示
   */
  getTurnDisplay() {
    if (this.status === GAME_STATUS.FINISHED) {
      return '游戏结束';
    }
    if (this.status === GAME_STATUS.NOT_STARTED) {
      return '等待游戏开始...';
    }
    
    const turnIcon = this.turn === 'Red' ? '🔴' : '⚫';
    return `${turnIcon} ${this.turn}方回合 (第${this.turnNumber}回合)`;
  }

  /**
   * 获取游戏结果显示
   */
  getResultDisplay() {
    if (!this.result) {
      return '';
    }
    
    const resultDisplayMap = {
      [GAME_RESULT.RED_WIN]: '🔴 红方胜利',
      [GAME_RESULT.BLACK_WIN]: '⚫ 黑方胜利',
      [GAME_RESULT.DRAW]: '⚔️ 和棋',
    };
    
    let display = resultDisplayMap[this.result] || this.result;
    
    if (this.resultReason) {
      display += ` - ${this.resultReason}`;
    }
    
    return display;
  }

  /**
   * 格式化走步历史
   */
  formatMoveHistory() {
    if (!this.moveHistory || this.moveHistory.length === 0) {
      return '暂无走步记录';
    }
    
    let output = '';
    for (let i = 0; i < this.moveHistory.length; i += 2) {
      const moveNum = Math.floor(i / 2) + 1;
      const redMove = this.moveHistory[i] || '';
      const blackMove = this.moveHistory[i + 1] || '';
      output += `${moveNum}. ${redMove}`;
      if (blackMove) {
        output += ` | ${blackMove}`;
      }
      output += '\n';
    }
    
    return output.trim() || '暂无走步记录';
  }

  /**
   * 重置状态
   */
  reset() {
    this.status = GAME_STATUS.NOT_STARTED;
    this.phase = GAME_PHASE.NOT_STARTED;
    this.turn = 'Red';
    this.turnNumber = 0;
    this.fen = '';
    this.players = {
      Red: { name: '红方', model: '' },
      Black: { name: '黑方', model: '' }
    };
    this.moveHistory = [];
    this.lastMove = null;
    this.result = null;
    this.resultReason = null;
    this.endReason = null;
    this._positionCounter = {};
    
    this._notifyListeners('reset', {});
  }

  /**
   * 导出完整状态
   */
  exportState() {
    return {
      status: this.status,
      phase: this.phase,
      turn: this.turn,
      turnNumber: this.turnNumber,
      fen: this.fen,
      players: this.players,
      moveHistory: this.moveHistory,
      lastMove: this.lastMove,
      result: this.result,
      resultReason: this.resultReason,
      endReason: this.endReason,
      endReasonDisplay: this.getEndReasonDisplay(),
      boardLayout: this.getBoardLayoutWith3D(),
    };
  }
}

// 导出到全局
window.GameStateManager = GameStateManager;
window.GAME_STATUS = GAME_STATUS;
window.GAME_PHASE = GAME_PHASE;
window.GAME_RESULT = GAME_RESULT;
window.GAME_END_REASON = GAME_END_REASON;
window.PIECE_NAMES = PIECE_NAMES;
