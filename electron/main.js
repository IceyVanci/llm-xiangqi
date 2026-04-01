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
// 中国象棋裁判引擎
// ============================================

const INITIAL_FEN = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1';

class XiangqiEngine {
    constructor(fen = INITIAL_FEN) {
        this.current_fen = fen;
        this.move_history = [];
        this.board = [];
        this.current_color = 'Red';
        this.position_history = [];
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
        
        this.current_color = parts[1] === 'w' ? 'Red' : 'Black';
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
        fen += this.current_color === 'Red' ? ' w' : ' b';
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

    get_legal_moves() {
        const moves = [];
        const color = this.current_color;
        
        for (let r = 0; r < 10; r++) {
            for (let c = 0; c < 9; c++) {
                const piece = this.board[r][c];
                if (!piece) continue;
                
                const is_red = this.is_red_piece(piece);
                if ((color === 'Red' && !is_red) || (color === 'Black' && is_red)) continue;
                
                const piece_moves = this._get_piece_moves(c, r, piece);
                for (const [tc, tr] of piece_moves) {
                    const from_iccs = String.fromCharCode(97 + c) + r;
                    const to_iccs = String.fromCharCode(97 + tc) + tr;
                    const move = from_iccs + to_iccs;
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
            case 'k':
                for (const [dc, dr] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
                    const nc = col + dc, nr = row + dr;
                    if (this.is_valid_position(nc, nr)) {
                        if (this.is_red_piece(piece) && nr > 2) continue;
                        if (this.is_black_piece(piece) && nr < 7) continue;
                        if (nc < 3 || nc > 5) continue;
                        moves.push([nc, nr]);
                    }
                }
                break;
            case 'a':
                for (const [dc, dr] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
                    const nc = col + dc, nr = row + dr;
                    if (this.is_valid_position(nc, nr)) {
                        if (this.is_red_piece(piece) && nr > 2) continue;
                        if (this.is_black_piece(piece) && nr < 7) continue;
                        if (nc < 3 || nc > 5) continue;
                        moves.push([nc, nr]);
                    }
                }
                break;
            case 'b':
                for (const [dc, dr] of [[2, 2], [2, -2], [-2, 2], [-2, -2]]) {
                    const nc = col + dc, nr = row + dr;
                    const eye_c = col + dc / 2, eye_r = row + dr / 2;
                    if (this.is_valid_position(nc, nr) && this.is_valid_position(eye_c, eye_r)) {
                        if (this.is_red_piece(piece) && nr > 4) continue;
                        if (this.is_black_piece(piece) && nr < 5) continue;
                        if (this.board[eye_r][eye_c]) continue;
                        moves.push([nc, nr]);
                    }
                }
                break;
            case 'n':
                for (const [[dc, dr], [ndc, ndr]] of [
                    [[-1, 0], [-2, -1]], [[-1, 0], [-2, 1]], [[1, 0], [2, -1]], [[1, 0], [2, 1]],
                    [[0, -1], [-1, -2]], [[0, -1], [1, -2]], [[0, 1], [-1, 2]], [[0, 1], [1, 2]]
                ]) {
                    const lc = col + dc, lr = row + dr;
                    const nc = col + ndc, nr = row + ndr;
                    if (this.is_valid_position(nc, nr) && this.is_valid_position(lc, lr)) {
                        if (this.board[lr][lc]) continue;
                        moves.push([nc, nr]);
                    }
                }
                break;
            case 'r':
                for (const [dc, dr] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
                    for (let i = 1; i < 10; i++) {
                        const nc = col + dc * i, nr = row + dr * i;
                        if (!this.is_valid_position(nc, nr)) break;
                        moves.push([nc, nr]);
                        if (this.board[nr][nc]) break;
                    }
                }
                break;
            case 'c':
                for (const [dc, dr] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
                    let screen = false;
                    for (let i = 1; i < 10; i++) {
                        const nc = col + dc * i, nr = row + dr * i;
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
            case 'p':
                const forward = this.is_red_piece(piece) ? 1 : -1;
                const nr = row + forward;
                if (this.is_valid_position(col, nr)) moves.push([col, nr]);
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
        
        this.board[to_r][to_c] = piece;
        this.board[from_r][from_c] = null;
        
        const in_check = this.is_king_in_check(this.current_color);
        
        this.board[from_r][from_c] = piece;
        this.board[to_r][to_c] = target;
        
        return !in_check;
    }

    find_king(color) {
        const king = color === 'Red' ? 'K' : 'k';
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
        
        const enemy = color === 'Red' ? 'Black' : 'Red';
        for (let r = 0; r < 10; r++) {
            for (let c = 0; c < 9; c++) {
                const piece = this.board[r][c];
                if (!piece) continue;
                if ((enemy === 'Red' && !this.is_red_piece(piece)) ||
                    (enemy === 'Black' && !this.is_black_piece(piece))) continue;
                
                const moves = this._get_piece_moves(c, r, piece);
                for (const [mc, mr] of moves) {
                    if (mc === king_pos[0] && mr === king_pos[1]) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    validate_move(iccs_move) {
        const moves = this.get_legal_moves();
        return moves.includes(iccs_move.toLowerCase());
    }

    apply_move(iccs_move) {
        const from = iccs_move.substring(0, 2);
        const to = iccs_move.substring(2, 4);
        const from_c = from.charCodeAt(0) - 97;
        const from_r = parseInt(from[1]);
        const to_c = to.charCodeAt(0) - 97;
        const to_r = parseInt(to[1]);
        
        const captured = this.board[to_r][to_c];
        this.board[to_r][to_c] = this.board[from_r][from_c];
        this.board[from_r][from_c] = null;
        
        this.current_color = this.current_color === 'Red' ? 'Black' : 'Red';
        this.current_fen = this.to_fen();
        this.move_history.push(iccs_move);
        this.position_history.push(this.current_fen);
        
        return { fen: this.current_fen, captured };
    }

    check_game_end() {
        const in_check = this.is_king_in_check(this.current_color);
        const legal_moves = this.get_legal_moves();
        
        if (legal_moves.length === 0) {
            if (in_check) {
                return {
                    ended: true,
                    winner: this.current_color === 'Red' ? 'black_win' : 'red_win',
                    reason: '被将死'
                };
            }
            return { ended: true, winner: 'draw', reason: '被困毙' };
        }
        
        return { ended: false };
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
}

// ============================================
// 全局变量
// ============================================

let mainWindow = null;
let wss = null;
let httpServer = null;
let engine = null;
let gameRunning = false;
let connectedClients = [];

// ============================================
// HTTP 服务器
// ============================================

function handleHttpRequest(req, res) {
    const url = req.url.split('?')[0];
    
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
    } else if (url === '/3d' || url === '/3d.html') {
        filePath = path.join(filePath, '3d.html');
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
            ws.send(JSON.stringify({ type: 'server.error', payload: { code: 'PARSE_ERROR', message: e.message } }));
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
        if (client.readyState === WebSocket.OPEN) {
            client.send(msg);
        }
    }
}

function handleMessage(ws, msg) {
    switch (msg.type) {
        case 'start_game':
            startGame(msg.config);
            break;
        case 'stop_game':
            stopGame();
            break;
        case 'reset_game':
            resetGame();
            break;
        case 'client.ready':
            // 客户端就绪
            console.log('[WS] Client ready');
            break;
        case 'client.ping':
            ws.send(JSON.stringify({ type: 'server.pong', timestamp: Date.now(), payload: msg.payload }));
            break;
    }
}

// ============================================
// 游戏逻辑
// ============================================

async function startGame(config) {
    if (gameRunning) {
        broadcast({ type: 'server.error', payload: { code: 'GAME_RUNNING', message: '游戏已在运行' } });
        return;
    }
    
    console.log('[Game] Starting...');
    gameRunning = true;
    engine = new XiangqiEngine();
    
    // 发送游戏初始化
    broadcast({
        type: 'game.init',
        payload: {
            fen: engine.current_fen,
            turn: engine.current_color,
            turn_number: 1,
            status: 'playing',
            players: {
                Red: { name: '红方 AI', model: config.red.model },
                Black: { name: '黑方 AI', model: config.black.model }
            },
            move_history: []
        }
    });
    
    let turnNumber = 1;
    
    while (gameRunning) {
        const legalMoves = engine.get_legal_moves();
        if (legalMoves.length === 0) break;
        
        const currentTurn = engine.current_color;
        const agentConfig = currentTurn === 'Red' ? config.red : config.black;
        
        try {
            const move = await callLLM(agentConfig, engine, currentTurn, legalMoves);
            
            if (!move || !engine.validate_move(move)) {
                console.warn(`[Game] Invalid move from ${currentTurn}: ${move}, using random`);
                move = legalMoves[Math.floor(Math.random() * legalMoves.length)];
            }
            
            const result = engine.apply_move(move);
            
            broadcast({
                type: 'game.move',
                payload: {
                    move: move,
                    from_pos: move.substring(0, 2),
                    to_pos: move.substring(2, 4),
                    piece: engine.board[parseInt(move[3])][move.charCodeAt(2) - 97],
                    captured: result.captured,
                    fen_after: result.fen,
                    turn: engine.current_color,
                    turn_number: turnNumber
                }
            });
            
            // 黑方走完后，回合数+1
            if (currentTurn === 'Black') {
                turnNumber++;
            }
            
            console.log(`[Game] ${currentTurn}: ${move}`);
            
            // 检查游戏结束
            const gameResult = engine.check_game_end();
            if (gameResult.ended) {
                broadcast({
                    type: 'game.game_over',
                    payload: {
                        result: gameResult.winner,
                        result_reason: gameResult.reason,
                        move_history: engine.move_history
                    }
                });
                break;
            }
        } catch (e) {
            console.error('[Game] Error:', e.message);
            broadcast({ type: 'server.error', payload: { code: 'GAME_ERROR', message: e.message } });
            break;
        }
        
        await new Promise(r => setTimeout(r, 500)); // 延迟
    }
    
    gameRunning = false;
}

/**
 * 停止游戏 - 保持棋盘状态，只停止 LLM 对话
 */
function stopGame() {
    console.log('[Game] Stopping game...');
    gameRunning = false;
    
    // 通知所有客户端游戏已停止
    broadcast({
        type: 'game.stopped',
        payload: {
            status: 'stopped',
            fen: engine ? engine.current_fen : INITIAL_FEN,
            move_history: engine ? engine.move_history : []
        }
    });
    
    console.log('[Game] Game stopped');
}

/**
 * 重置游戏到初始状态
 */
function resetGame() {
    console.log('[Game] Resetting game...');
    gameRunning = false;
    engine = new XiangqiEngine();
    
    // 通知所有客户端游戏已重置
    broadcast({
        type: 'game.init',
        payload: {
            fen: engine.current_fen,
            turn: engine.current_color,
            turn_number: 1,
            status: 'playing',
            players: {
                Red: { name: '红方 AI', model: '' },
                Black: { name: '黑方 AI', model: '' }
            },
            move_history: []
        }
    });
    
    console.log('[Game] Game reset complete');
}

async function callLLM(config, engine, color, legalMoves) {
    const prompt = `你是中国象棋AI。你执${color === 'Red' ? '红方' : '黑方'}。
当前局面（FEN）: ${engine.current_fen}
棋盘:
${engine.render_ascii_board()}
合法走步: ${legalMoves.join(', ')}

请选择一个走步，输出格式：{"move": "e2e4"}
只输出JSON，不要其他内容。`;

    try {
        // 发送 AI 日志（prompt）
        broadcast({
            type: 'game.ai_log',
            payload: {
                color: color,
                type: 'prompt',
                text: prompt
            }
        });
        
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
        
        // 发送 AI 日志（response）
        broadcast({
            type: 'game.ai_log',
            payload: {
                color: color,
                type: 'response',
                text: content || '(空响应)'
            }
        });
        
        if (!content) {
            console.log('[LLM] Empty response, using random move');
            return legalMoves[Math.floor(Math.random() * legalMoves.length)];
        }
        
        // 尝试解析 JSON
        const jsonMatch = content.match(/"move"\s*:\s*"([^"]+)"/i);
        if (jsonMatch && legalMoves.includes(jsonMatch[1].toLowerCase())) {
            return jsonMatch[1].toLowerCase();
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
        
        // 发送错误日志
        broadcast({
            type: 'game.ai_log',
            payload: {
                color: color,
                type: 'response',
                text: `错误: ${e.message}`
            }
        });
        
        return legalMoves[Math.floor(Math.random() * legalMoves.length)];
    }
}

// ============================================
// IPC 处理器 - 配置管理
// ============================================

ipcMain.handle('get-config', async () => {
    return {
        redModel: store.get('redModel', ''),
        redBaseUrl: store.get('redBaseUrl', ''),
        blackModel: store.get('blackModel', ''),
        blackBaseUrl: store.get('blackBaseUrl', ''),
        hasApiKeys: !!(store.get('redApiKey') && store.get('blackApiKey')),
    };
});

ipcMain.handle('save-config', async (event, config) => {
    if (config.redApiKey) store.set('redApiKey', config.redApiKey);
    if (config.redModel) store.set('redModel', config.redModel);
    if (config.redBaseUrl) store.set('redBaseUrl', config.redBaseUrl);
    if (config.blackApiKey) store.set('blackApiKey', config.blackApiKey);
    if (config.blackModel) store.set('blackModel', config.blackModel);
    if (config.blackBaseUrl) store.set('blackBaseUrl', config.blackBaseUrl);
    return { success: true };
});

ipcMain.handle('clear-config', async () => {
    store.clear();
    return { success: true };
});

ipcMain.handle('get-version', async () => {
    return '1.0.0';
});

// ============================================
// Electron 主进程
// ============================================

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1600,
        height: 900,
        title: 'LLM-Xiangqi 3D',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
    });
    
    mainWindow.loadURL('http://localhost:8888/3d');
    
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startServers() {
    httpServer = http.createServer(handleHttpRequest);
    httpServer.listen(8888, () => {
        console.log('[HTTP] Server started on http://localhost:8888');
    });
    
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
    gameRunning = false;
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    gameRunning = false;
    if (httpServer) httpServer.close();
    if (wss) wss.close();
});
