/**
 * LLM-Xiangqi Electron 主进程
 * 
 * 功能：
 * 1. HTTP 服务器 - 提供前端界面
 * 2. WebSocket 服务器 - 处理游戏通信
 * 3. 中国象棋裁判引擎 - 走棋验证、游戏规则
 * 4. LLM API 调用 - 与 AI Agent 通信
 */

const { app, BrowserWindow, ipcMain } = require('electron');
const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
const axios = require('axios');
const Store = require('electron-store');

// ============================================
// 加密存储配置
// ============================================

const store = new Store({
    name: 'llm-xiangqi-config',
    encryptionKey: 'llm-xiangqi-v1-secure-key-2024',
    schema: {
        redApiKey: { type: 'string' },
        redModel: { type: 'string' },
        redBaseUrl: { type: 'string' },
        blackApiKey: { type: 'string' },
        blackModel: { type: 'string' },
        blackBaseUrl: { type: 'string' },
    }
});

// ============================================
// 中国象棋裁判引擎 (JavaScript 实现)
// ============================================

const INITIAL_FEN = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1';

const PIECE_NAMES = {
    'K': '将', 'k': '帅',
    'A': '仕', 'a': '士',
    'B': '相', 'b': '象',
    'N': '马', 'n': '马',
    'R': '车', 'r': '车',
    'C': '炮', 'c': '炮',
    'P': '兵', 'p': '卒',
};

class XiangqiEngine {
    constructor(fen = INITIAL_FEN) {
        this.current_fen = fen;
        this.move_history = [];
        this.board = [];
        this.current_color = 'red';
        this.position_history = [];
        this.check_history = [];
        this._parse_fen(fen);
    }

    _parse_fen(fen) {
        const parts = fen.split(' ');
        const rows = parts[0].split('/');
        
        this.board = Array(10).fill(null).map(() => Array(9).fill(null));
        
        for (let r = 0; r < 10; r++) {
            let c = 0;
            for (const char of rows[9 - r]) {
                if (char >= '1' && char <= '9') {
                    c += parseInt(char);
                } else {
                    this.board[r][c] = char;
                    c++;
                }
            }
        }
        
        this.current_color = parts[1] === 'w' ? 'red' : 'black';
    }

    to_fen() {
        let fen = '';
        for (let r = 9; r >= 0; r--) {
            let empty = 0;
            for (let c = 0; c < 9; c++) {
                if (this.board[r][c]) {
                    if (empty > 0) {
                        fen += empty;
                        empty = 0;
                    }
                    fen += this.board[r][c];
                } else {
                    empty++;
                }
            }
            if (empty > 0) fen += empty;
            if (r > 0) fen += '/';
        }
        fen += this.current_color === 'red' ? ' w' : ' b';
        return fen + ' - - 0 1';
    }

    is_red_piece(p) {
        return p && p.toUpperCase() === p;
    }

    is_black_piece(p) {
        return p && p.toLowerCase() === p;
    }

    is_valid_position(col, row) {
        return col >= 0 && col <= 8 && row >= 0 && row <= 9;
    }

    // 获取合法走步
    get_legal_moves() {
        const moves = [];
        const color = this.current_color;
        
        for (let r = 0; r < 10; r++) {
            for (let c = 0; c < 9; c++) {
                const piece = this.board[r][c];
                if (!piece) continue;
                
                const is_red = this.is_red_piece(piece);
                if ((color === 'red' && !is_red) || (color === 'black' && is_red)) continue;
                
                const piece_moves = this._get_piece_moves(c, r, piece);
                for (const [tc, tr] of piece_moves) {
                    const move = `${String.fromCharCode(97+c)}${r}${String.fromCharCode(97+tc)}${tr}`;
                    if (this._is_move_legal(c, r, tc, tr, piece)) {
                        moves.push(move);
                    }
                }
            }
        }
        return moves;
    }

    _get_piece_moves(col, row, piece) {
        const moves = [];
        const p = piece.toLowerCase();
        
        switch (p) {
            case 'k': // 将/帅
                for (const [dc, dr] of [[0,1],[0,-1],[1,0],[-1,0]]) {
                    const nc = col + dc, nr = row + dr;
                    if (this.is_valid_position(nc, nr)) {
                        // 九宫限制
                        if (this.is_red_piece(piece) && nr > 2) continue;
                        if (this.is_black_piece(piece) && nr < 7) continue;
                        if (nc < 3 || nc > 5) continue;
                        moves.push([nc, nr]);
                    }
                }
                break;
            case 'a': // 仕/士
                for (const [dc, dr] of [[1,1],[1,-1],[-1,1],[-1,-1]]) {
                    const nc = col + dc, nr = row + dr;
                    if (this.is_valid_position(nc, nr)) {
                        if (this.is_red_piece(piece) && nr > 2) continue;
                        if (this.is_black_piece(piece) && nr < 7) continue;
                        if (nc < 3 || nc > 5) continue;
                        moves.push([nc, nr]);
                    }
                }
                break;
            case 'b': // 相/象
                for (const [dc, dr] of [[2,2],[2,-2],[-2,2],[-2,-2]]) {
                    const nc = col + dc, nr = row + dr;
                    const eye_c = col + dc/2, eye_r = row + dr/2;
                    if (this.is_valid_position(nc, nr) && this.is_valid_position(eye_c, eye_r)) {
                        if (this.is_red_piece(piece) && nr > 4) continue;
                        if (this.is_black_piece(piece) && nr < 5) continue;
                        if (this.board[eye_r][eye_c]) continue; // 塞象眼
                        moves.push([nc, nr]);
                    }
                }
                break;
            case 'n': // 马
                for (const [[dc, dr], [ndc, ndr]] of [
                    [[-1,0],[-2,-1]],[[-1,0],[-2,1]],[[1,0],[2,-1]],[[1,0],[2,1]],
                    [[0,-1],[-1,-2]],[[0,-1],[1,-2]],[[0,1],[-1,2]],[[0,1],[1,2]]
                ]) {
                    const lc = col + dc, lr = row + dr;
                    const nc = col + ndc, nr = row + ndr;
                    if (this.is_valid_position(nc, nr) && this.is_valid_position(lc, lr)) {
                        if (this.board[lr][lc]) continue; // 蹩马腿
                        moves.push([nc, nr]);
                    }
                }
                break;
            case 'r': // 车
                for (const [dc, dr] of [[0,1],[0,-1],[1,0],[-1,0]]) {
                    for (let i = 1; i < 10; i++) {
                        const nc = col + dc*i, nr = row + dr*i;
                        if (!this.is_valid_position(nc, nr)) break;
                        moves.push([nc, nr]);
                        if (this.board[nr][nc]) break;
                    }
                }
                break;
            case 'c': // 炮
                for (const [dc, dr] of [[0,1],[0,-1],[1,0],[-1,0]]) {
                    let screen = false;
                    for (let i = 1; i < 10; i++) {
                        const nc = col + dc*i, nr = row + dr*i;
                        if (!this.is_valid_position(nc, nr)) break;
                        if (!screen) {
                            if (this.board[nr][nc]) screen = true;
                            else moves.push([nc, nr]);
                        } else {
                            if (this.board[nr][nc]) {
                                moves.push([nc, nr]);
                                break;
                            }
                        }
                    }
                }
                break;
            case 'p': // 兵/卒
                const forward = this.is_red_piece(piece) ? 1 : -1;
                const nr = row + forward;
                if (this.is_valid_position(col, nr)) moves.push([col, nr]);
                // 过河后可左右移动
                const crossed = this.is_red_piece(piece) ? row < 5 : row > 4;
                if (crossed) {
                    for (const dc of [-1, 1]) {
                        const nc = col + dc;
                        if (this.is_valid_position(nc, row)) moves.push([nc, row]);
                    }
                }
                break;
        }
        return moves;
    }

    _is_move_legal(from_c, from_r, to_c, to_r, piece) {
        const target = this.board[to_r][to_c];
        if (target) {
            if (this.is_red_piece(piece) && this.is_red_piece(target)) return false;
            if (this.is_black_piece(piece) && this.is_black_piece(target)) return false;
        }
        
        // 临时移动
        this.board[to_r][to_c] = piece;
        this.board[from_r][from_c] = null;
        
        const in_check = this.is_king_in_check(this.current_color);
        
        // 恢复
        this.board[from_r][from_c] = piece;
        this.board[to_r][to_c] = target;
        
        return !in_check;
    }

    find_king(color) {
        const king = color === 'red' ? 'K' : 'k';
        for (let r = 0; r < 10; r++) {
            for (let c = 0; c < 9; c++) {
                if (this.board[r][c] === king) return [c, r];
            }
        }
        return null;
    }

    is_king_in_check(color) {
        const king_pos = this.find_king(color);
        if (!king_pos) return false;
        
        const enemy = color === 'red' ? 'black' : 'red';
        for (let r = 0; r < 10; r++) {
            for (let c = 0; c < 9; c++) {
                const piece = this.board[r][c];
                if (!piece) continue;
                if ((enemy === 'red' && !this.is_red_piece(piece)) || 
                    (enemy === 'black' && !this.is_black_piece(piece))) continue;
                
                const moves = this._get_piece_moves(c, r, piece);
                for (const [mc, mr] of moves) {
                    if (mc === king_pos[0] && mr === king_pos[1]) {
                        // 进一步验证
                        if (this._can_attack(c, r, king_pos[0], king_pos[1], piece)) {
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }

    _can_attack(from_c, from_r, to_c, to_r, piece) {
        // 简化：假设已经在合法移动列表中就是可以攻击的
        return true;
    }

    validate_move(iccs_move) {
        const moves = this.get_legal_moves();
        return moves.includes(iccs_move.toLowerCase());
    }

    apply_move(iccs_move) {
        if (!this.validate_move(iccs_move)) {
            throw new Error(`Invalid move: ${iccs_move}`);
        }
        
        const from = iccs_move.substring(0, 2);
        const to = iccs_move.substring(2, 4);
        const from_c = from.charCodeAt(0) - 97;
        const from_r = parseInt(from[1]);
        const to_c = to.charCodeAt(0) - 97;
        const to_r = parseInt(to[1]);
        
        this.board[to_r][to_c] = this.board[from_r][from_c];
        this.board[from_r][from_c] = null;
        
        this.current_color = this.current_color === 'red' ? 'black' : 'red';
        this.current_fen = this.to_fen();
        this.move_history.push(iccs_move);
        this.position_history.push(this.current_fen);
        
        return this.current_fen;
    }

    render_ascii_board() {
        let board = '    a   b   c   d   e   f   g   h   i\n';
        board += '  +---+---+---+---+---+---+---+---+---+\n';
        for (let r = 9; r >= 0; r--) {
            board += `${r} |`;
            for (let c = 0; c < 9; c++) {
                const piece = this.board[r][c];
                board += ` ${piece || ' '} |`;
            }
            board += '\n  +---+---+---+---+---+---+---+---+---+\n';
        }
        return board;
    }

    check_game_end() {
        // 检查将军
        const in_check = this.is_king_in_check(this.current_color);
        const legal_moves = this.get_legal_moves();
        
        if (legal_moves.length === 0) {
            if (in_check) {
                return { ended: true, winner: this.current_color === 'red' ? 'black' : 'red', reason: '被将死' };
            }
            return { ended: true, winner: 'draw', reason: '被困毙' };
        }
        
        return { ended: false };
    }
}

// ============================================
// 全局变量
// ============================================

let mainWindow = null;
let wss = null;
let httpServer = null;
let gameController = null;
let connectedClients = [];

// ============================================
// HTTP 服务器
// ============================================

function handleHttpRequest(req, res) {
    const url = req.url.split('?')[0];
    
    // CORS 头
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    let filePath = path.join(__dirname, 'src', 'renderer');
    
    if (url === '/' || url === '/index.html') {
        filePath = path.join(filePath, 'index.html');
    } else if (url === '/3d') {
        filePath = path.join(filePath, '3d.html');
    } else if (url === '/config') {
        // 返回配置页面
        filePath = path.join(filePath, 'index.html');
    } else {
        filePath = path.join(filePath, url);
    }
    
    fs.readFile(filePath, (err, data) => {
        if (err) {
            res.writeHead(404, { 'Content-Type': 'text/html' });
            res.end('<h1>404 Not Found</h1>');
            return;
        }
        
        const ext = path.extname(filePath);
        const contentTypes = {
            '.html': 'text/html',
            '.js': 'application/javascript',
            '.css': 'text/css',
            '.json': 'application/json',
        };
        
        res.writeHead(200, { 'Content-Type': contentTypes[ext] || 'text/plain' });
        res.end(data);
    });
}

// ============================================
// WebSocket 服务器
// ============================================

function handleWebSocket(ws) {
    connectedClients.push(ws);
    console.log(`[WS] Client connected. Total: ${connectedClients.length}`);
    
    ws.on('message', (data) => {
        try {
            const msg = JSON.parse(data);
            handleMessage(ws, msg);
        } catch (e) {
            console.error('[WS] Parse error:', e);
        }
    });
    
    ws.on('close', () => {
        connectedClients = connectedClients.filter(c => c !== ws);
        console.log(`[WS] Client disconnected. Total: ${connectedClients.length}`);
    });
}

function broadcast(data) {
    const msg = JSON.stringify(data);
    for (const client of connectedClients) {
        if (client.readyState === 1) {
            client.send(msg);
        }
    }
}

function handleMessage(ws, msg) {
    switch (msg.type) {
        case 'start_game':
            startGame(msg.config);
            break;
        case 'get_state':
            sendState(ws);
            break;
    }
}

// ============================================
// 游戏逻辑
// ============================================

async function startGame(config) {
    console.log('[Game] Starting...');
    broadcast({ type: 'game_started', fen: INITIAL_FEN, turn: 'Red' });
    
    const engine = new XiangqiEngine();
    
    while (true) {
        const state = engine.get_legal_moves();
        if (state.length === 0) break;
        
        const currentTurn = engine.current_color;
        const turnName = currentTurn === 'red' ? 'Red' : 'Black';
        const agentConfig = currentTurn === 'red' ? config.red : config.black;
        
        // 调用 LLM
        try {
            const move = await callLLM(agentConfig, engine, currentTurn);
            
            if (move && engine.validate_move(move)) {
                engine.apply_move(move);
                
                broadcast({
                    type: 'move',
                    move: move,
                    move_by: turnName,
                    fen: engine.current_fen,
                    ascii_board: engine.render_ascii_board(),
                });
                
                console.log(`[Game] ${turnName}: ${move}`);
                
                // 检查游戏结束
                const result = engine.check_game_end();
                if (result.ended) {
                    broadcast({ type: 'game_over', result: result.winner, reason: result.reason });
                    break;
                }
            }
        } catch (e) {
            console.error('[Game] LLM error:', e);
            broadcast({ type: 'error', message: e.message });
            break;
        }
        
        await new Promise(r => setTimeout(r, 1000)); // 延迟
    }
}

async function callLLM(config, engine, color) {
    const legalMoves = engine.get_legal_moves();
    if (legalMoves.length === 0) return null;
    
    const prompt = `你是中国象棋AI。你执${color === 'red' ? '红方' : '黑方'}。
当前局面（FEN）: ${engine.current_fen}
棋盘:
${engine.render_ascii_board()}
合法走步: ${legalMoves.join(', ')}

请选择一个走步，输出格式：{"move": "e2e4"}
只输出JSON，不要其他内容。`;

    try {
        const response = await axios.post(`${config.baseUrl}/chat/completions`, {
            model: config.model,
            messages: [{ role: 'user', content: prompt }],
            temperature: config.temperature || 0.7,
            max_tokens: config.maxTokens || 2048,
        }, {
            headers: {
                'Authorization': `Bearer ${config.apiKey}`,
                'Content-Type': 'application/json',
            },
            timeout: 60000,
        });
        
        const content = response.data?.choices?.[0]?.message?.content;
        if (!content) {
            console.log('[LLM] Empty response, using random move');
            return legalMoves[Math.floor(Math.random() * legalMoves.length)];
        }
        
        const match = content.match(/"move"\s*:\s*"([^"]+)"/i);
        if (match && legalMoves.includes(match[1].toLowerCase())) {
            return match[1].toLowerCase();
        }
        
        // 尝试 ICCS 格式
        const iccsMatch = content.match(/([a-i]\d[a-i]\d)/i);
        if (iccsMatch && legalMoves.includes(iccsMatch[1].toLowerCase())) {
            return iccsMatch[1].toLowerCase();
        }
        
        console.log('[LLM] Could not parse move, using random');
        return legalMoves[Math.floor(Math.random() * legalMoves.length)];
    } catch (e) {
        console.error('[LLM] Error:', e.message);
        return legalMoves[Math.floor(Math.random() * legalMoves.length)];
    }
}

function sendState(ws) {
    if (gameController) {
        ws.send(JSON.stringify({
            type: 'state',
            fen: gameController.current_fen,
            turn: gameController.current_color,
            moves: gameController.get_legal_moves(),
        }));
    }
}

// ============================================
// IPC 处理器 - 配置管理
// ============================================

// 获取保存的配置（不包含 API Key 明文）
ipcMain.handle('get-config', async () => {
    return {
        redModel: store.get('redModel', ''),
        redBaseUrl: store.get('redBaseUrl', ''),
        blackModel: store.get('blackModel', ''),
        blackBaseUrl: store.get('blackBaseUrl', ''),
        hasApiKeys: !!(store.get('redApiKey') && store.get('blackApiKey')),
    };
});

// 保存配置（包含 API Key 加密存储）
ipcMain.handle('save-config', async (event, config) => {
    if (config.redApiKey) store.set('redApiKey', config.redApiKey);
    if (config.redModel) store.set('redModel', config.redModel);
    if (config.redBaseUrl) store.set('redBaseUrl', config.redBaseUrl);
    if (config.blackApiKey) store.set('blackApiKey', config.blackApiKey);
    if (config.blackModel) store.set('blackModel', config.blackModel);
    if (config.blackBaseUrl) store.set('blackBaseUrl', config.blackBaseUrl);
    return { success: true };
});

// 清除所有配置
ipcMain.handle('clear-config', async () => {
    store.clear();
    return { success: true };
});

// ============================================
// Electron 主进程
// ============================================

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        title: 'LLM-Xiangqi',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
    });
    
    mainWindow.loadURL('http://localhost:8888/3d');
}

function startServers() {
    // HTTP 服务器
    httpServer = http.createServer(handleHttpRequest);
    httpServer.listen(8888, () => {
        console.log('[HTTP] Server started on http://localhost:8888');
    });
    
    // WebSocket 服务器
    wss = new WebSocket.Server({ server: httpServer });
    wss.on('connection', handleWebSocket);
    console.log('[WS] WebSocket server started');
}

app.whenReady().then(() => {
    startServers();
    createWindow();
    
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    if (httpServer) httpServer.close();
    if (wss) wss.close();
});
