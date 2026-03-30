/**
 * 游戏状态管理器
 * 
 * 功能:
 * - 管理游戏状态
 * - 解析 FEN
 * - 走步历史
 */

// 游戏状态枚举
const GAME_STATUS = {
  NOT_STARTED: 'not_started',
  PLAYING: 'playing',
  FINISHED: 'finished'
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

class GameStateManager {
  constructor() {
    this.status = GAME_STATUS.NOT_STARTED;
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
    this.listeners = [];
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
   * 从服务器初始化状态
   */
  initFromServer(state) {
    this.fen = state.fen || '';
    this.turn = state.turn || 'Red';
    this.turnNumber = state.turn_number || 1;
    this.status = state.status === 'finished' ? GAME_STATUS.FINISHED : GAME_STATUS.PLAYING;
    
    if (state.players) {
      this.players.Red = state.players.Red || { name: '红方', model: '' };
      this.players.Black = state.players.Black || { name: '黑方', model: '' };
    }
    
    if (state.move_history) {
      this.moveHistory = state.move_history;
    }
    
    if (state.last_move) {
      this.lastMove = state.last_move;
    }
    
    if (state.result) {
      this.result = state.result;
      this.resultReason = state.result_reason || '';
    }
    
    this._notifyListeners('init', state);
  }

  /**
   * 处理走步
   */
  handleMove(moveData) {
    this.fen = moveData.fen_after || moveData.fen || this.fen;
    this.turnNumber++;
    this.turn = this.turn === 'Red' ? 'Black' : 'Red';
    
    this.moveHistory.push(moveData.move);
    
    this.lastMove = {
      from: moveData.from_pos,
      to: moveData.to_pos,
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
    this.result = gameOverData.result;
    this.resultReason = gameOverData.result_reason || '';
    
    if (gameOverData.move_history) {
      this.moveHistory = gameOverData.move_history;
    }
    
    this._notifyListeners('game_over', gameOverData);
  }

  /**
   * 获取棋盘布局
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
            piece: char
          });
          col++;
        }
      }
    }
    
    return layout;
  }

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
    
    this._notifyListeners('reset', {});
  }
}

// 导出到全局
window.GameStateManager = GameStateManager;
window.GAME_STATUS = GAME_STATUS;
window.PIECE_NAMES = PIECE_NAMES;
