/**
 * 3D 场景管理器
 * 
 * 功能:
 * - WebGL 2.0 渲染器初始化
 * - 场景、相机、光照管理
 * - 棋盘和棋子渲染
 * - 选中/移动高亮特效
 */

// 渲染器类型
const RENDERER_TYPE = {
  WEBGPU: 'webgpu',
  WEBGL2: 'webgl2',
}

// 棋盘配置
const BOARD_CONFIG = {
  width: 9,      // 9 列
  height: 10,    // 10 行
  cellSize: 1.0,
  colors: {
    background: 0x0a0a0f,  // 深邃墨黑
    board: 0xf5e6c8,       // 明亮木纹色
    line: 0x4a3728,        // 深褐色线条
    river: 0x8b7355,       // 河界颜色 - 浅棕色，明显区分
  },
}

// 棋子配置
const PIECE_CONFIG = {
  radius: 0.38,
  height: 0.4,
  colors: {
    red: {
      body: 0xfffef8,   // 棋子本体 - 纯白，高对比
      text: 0xcc0000,   // 文字颜色 - 鲜红，醒目
      base: 0xd4a76a,   // 底座 - 金棕色
    },
    black: {
      body: 0xfffef8,   // 棋子本体 - 纯白，高对比
      text: 0x0a0a0a,   // 文字颜色 - 纯黑，醒目
      base: 0x6b5344,   // 底座 - 深棕灰
    },
  },
}

class SceneManager {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.options = {
      shadowMapSize: options.shadowMapSize || 2048,
      cameraPosition: options.cameraPosition || [8, 12, 12],
      lightFollowsCamera: options.lightFollowsCamera || false,
      ...options,
    };
    
    // 核心组件
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.controls = null;
    
    // 渲染器类型
    this.rendererType = null;
    
    // 对象引用
    this.boardGroup = null;
    this.piecesGroup = null;
    this.effectsGroup = null;
    
    // 棋子对象映射 (iccs -> mesh)
    this.pieces = new Map();
    
    // 动画管理器 (稍后初始化)
    this.animator = null;
    
    // 粒子系统 (稍后初始化)
    this.particles = null;
    
    // 音效管理器 (稍后初始化)
    this.sounds = null;
    
    // 选中状态
    this.selectedPiece = null;
    this._selectionHighlight = null;
    this._selectionAnimationId = null;
    
    // 动画循环
    this._animationId = null;
    this._isRunning = false;
    this._lastTime = 0;
  }

  /**
   * 初始化场景
   */
  async init() {
    // 初始化渲染器
    await this._initRenderer();
    
    // 创建场景
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(BOARD_CONFIG.colors.background);
    
    // 创建相机
    this._initCamera();
    
    // 创建控制器
    this._initControls();
    
    // 设置光照
    this._initLighting();
    
    // 创建场景对象容器
    this._initObjectGroups();
    
    // 创建棋盘
    this._createBoard();
    
    // 初始化动画管理器
    if (typeof MoveAnimator !== 'undefined') {
      this.animator = new MoveAnimator();
    }
    
    // 初始化粒子系统
    if (typeof ParticleSystem !== 'undefined') {
      this.particles = new ParticleSystem(this.scene);
    }
    
    // 初始化音效
    if (typeof SoundManager !== 'undefined') {
      this.sounds = new SoundManager();
      this.sounds.init();
    }
    
    // 开始渲染循环
    this._startRenderLoop();
    
    console.info('[Scene] Initialized with renderer:', this.rendererType);
  }

  /**
   * 初始化渲染器 (WebGL 2.0)
   */
  async _initRenderer() {
    // 检查 WebGL 2.0 支持
    const gl = this.canvas.getContext('webgl2');
    if (!gl) {
      throw new Error('WebGL 2.0 not supported by your browser');
    }
    
    // 创建 WebGL 2.0 渲染器
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
    this.rendererType = RENDERER_TYPE.WEBGL2;
    console.info('[Scene] Using WebGL 2.0 renderer');
    
    // 配置渲染器 - 使用 CSS 像素尺寸，确保响应式
    const cssWidth = this.canvas.clientWidth || this.canvas.offsetWidth || 800;
    const cssHeight = this.canvas.clientHeight || this.canvas.offsetHeight || 600;
    
    this.renderer.setSize(cssWidth, cssHeight, false); // false = 不设置 canvas.width/height
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    
    // 阴影配置
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.shadowMap.autoUpdate = true;
    
    // 处理窗口大小变化
    this._resizeHandler = () => this._handleResize();
    window.addEventListener('resize', this._resizeHandler);
  }

  /**
   * 初始化相机
   */
  _initCamera() {
    const aspect = this.canvas.clientWidth / this.canvas.clientHeight;
    this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 100);
    
    const [x, y, z] = this.options.cameraPosition;
    this.camera.position.set(x, y, z);
    this.camera.lookAt(0, 0, 0);
  }

  /**
   * 初始化控制器
   */
  _initControls() {
    this.controls = new THREE.OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.maxPolarAngle = Math.PI / 2.2;
    this.controls.minDistance = 5;
    this.controls.maxDistance = 30;
    this.controls.target.set(0, 0, 0);
  }

  /**
   * 初始化光照
   */
  _initLighting() {
    // 环境光 - 提高整体基础亮度
    const ambient = new THREE.AmbientLight(0xffffff, 0.7);
    this.scene.add(ambient);
    
    // 半球光 - 提供自然的上下光照（天空/地面颜色）
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe8dcc8, 0.6);
    hemiLight.position.set(0, 50, 0);
    this.scene.add(hemiLight);
    
    // 主光源 - 从上方45度角照射，均匀照亮整个棋盘
    const mainLight = new THREE.DirectionalLight(0xfff8f0, 1.2);
    mainLight.position.set(8, 20, 12);
    mainLight.target.position.set(0, 0, 0);
    mainLight.castShadow = true;
    
    // 阴影配置 - 确保覆盖整个棋盘（9列 x 10行）
    mainLight.shadow.mapSize.width = this.options.shadowMapSize;
    mainLight.shadow.mapSize.height = this.options.shadowMapSize;
    mainLight.shadow.camera.near = 1;
    mainLight.shadow.camera.far = 80;
    // 扩大阴影范围覆盖整个棋盘区域
    mainLight.shadow.camera.left = -12;
    mainLight.shadow.camera.right = 12;
    mainLight.shadow.camera.top = 12;
    mainLight.shadow.camera.bottom = -12;
    mainLight.shadow.bias = -0.0005;
    mainLight.shadow.radius = 2;
    mainLight.shadow.normalBias = 0.02;
    
    this.mainLight = mainLight;
    this.scene.add(mainLight);
    this.scene.add(mainLight.target);
    
    // 补光 - 从左侧照射，平衡阴影
    const fillLight = new THREE.DirectionalLight(0xfff0e6, 0.5);
    fillLight.position.set(-10, 15, 0);
    this.scene.add(fillLight);
    
    // 背面补光 - 减少背面暗角
    const backLight = new THREE.DirectionalLight(0xe6f0ff, 0.4);
    backLight.position.set(0, 10, -15);
    this.scene.add(backLight);
    
    // 底部环境光反射 - 模拟棋盘台面反射
    const bottomLight = new THREE.PointLight(0xf5e6c8, 0.3, 20);
    bottomLight.position.set(0, -5, 0);
    this.scene.add(bottomLight);
  }

  /**
   * 初始化对象分组
   */
  _initObjectGroups() {
    this.boardGroup = new THREE.Group();
    this.boardGroup.name = 'board';
    this.scene.add(this.boardGroup);
    
    this.piecesGroup = new THREE.Group();
    this.piecesGroup.name = 'pieces';
    this.scene.add(this.piecesGroup);
    
    this.effectsGroup = new THREE.Group();
    this.effectsGroup.name = 'effects';
    this.scene.add(this.effectsGroup);
  }

  /**
   * 创建程序化棋盘
   */
  _createBoard() {
    const { width, height, cellSize, colors } = BOARD_CONFIG;
    
    const boardWidth = width * cellSize + 0.5;
    const boardHeight = height * cellSize + 0.5;
    const boardThickness = 0.3;
    
    const baseGeometry = new THREE.BoxGeometry(boardWidth, boardThickness, boardHeight);
    const baseMaterial = new THREE.MeshStandardMaterial({
      color: colors.board,
      roughness: 0.7,
      metalness: 0.1,
    });
    const base = new THREE.Mesh(baseGeometry, baseMaterial);
    base.position.y = -boardThickness / 2;
    base.receiveShadow = true;
    this.boardGroup.add(base);
    
    this._createRiverArea();
    this._createGridLines();
    this._createRiverLabels();
  }

  /**
   * 创建河界区域
   */
  _createRiverArea() {
    const { cellSize, colors } = BOARD_CONFIG;
    
    const riverWidth = 8 * cellSize;
    const riverHeight = cellSize;
    
    const riverGeometry = new THREE.PlaneGeometry(riverWidth, riverHeight);
    const riverMaterial = new THREE.MeshStandardMaterial({
      color: colors.river,
      roughness: 0.9,
      metalness: 0.0,
    });
    
    const river = new THREE.Mesh(riverGeometry, riverMaterial);
    river.rotation.x = -Math.PI / 2;
    river.position.set(0, 0.002, 0);
    river.receiveShadow = true;
    
    this.boardGroup.add(river);
  }

  /**
   * 创建棋格线
   */
  _createGridLines() {
    const { width, height, cellSize, colors } = BOARD_CONFIG;
    const lineMaterial = new THREE.LineBasicMaterial({ color: colors.line, linewidth: 2 });
    
    const halfWidth = (width - 1) * cellSize / 2;
    const halfHeight = (height - 1) * cellSize / 2;
    
    const riverTopZ = -halfHeight + 4 * cellSize;
    const riverBottomZ = -halfHeight + 5 * cellSize;
    
    // 横线
    for (let row = 0; row < height; row++) {
      const z = -halfHeight + row * cellSize;
      const points = [
        new THREE.Vector3(-halfWidth, 0.005, z),
        new THREE.Vector3(halfWidth, 0.005, z),
      ];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      this.boardGroup.add(new THREE.Line(geometry, lineMaterial));
    }
    
    // 竖线
    for (let col = 0; col < width; col++) {
      const x = -halfWidth + col * cellSize;
      
      if (col === 0 || col === 8) {
        const points = [
          new THREE.Vector3(x, 0.005, -halfHeight),
          new THREE.Vector3(x, 0.005, halfHeight),
        ];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        this.boardGroup.add(new THREE.Line(geometry, lineMaterial));
      } else {
        const pointsTop = [
          new THREE.Vector3(x, 0.005, -halfHeight),
          new THREE.Vector3(x, 0.005, riverTopZ),
        ];
        const geometryTop = new THREE.BufferGeometry().setFromPoints(pointsTop);
        this.boardGroup.add(new THREE.Line(geometryTop, lineMaterial));
        
        const pointsBottom = [
          new THREE.Vector3(x, 0.005, riverBottomZ),
          new THREE.Vector3(x, 0.005, halfHeight),
        ];
        const geometryBottom = new THREE.BufferGeometry().setFromPoints(pointsBottom);
        this.boardGroup.add(new THREE.Line(geometryBottom, lineMaterial));
      }
    }
    
    this._createPalaceLines(halfWidth, halfHeight, cellSize, lineMaterial);
  }

  /**
   * 创建九宫格斜线
   */
  _createPalaceLines(halfWidth, halfHeight, cellSize, material) {
    const leftCol = -halfWidth + 3 * cellSize;
    const rightCol = -halfWidth + 5 * cellSize;
    
    // 红方九宫
    const redTopZ = (4.5 - 2) * cellSize;
    const redBottomZ = (4.5 - 0) * cellSize;
    
    const redTopLeft = new THREE.Vector3(leftCol, 0.005, redTopZ);
    const redTopRight = new THREE.Vector3(rightCol, 0.005, redTopZ);
    const redBottomLeft = new THREE.Vector3(leftCol, 0.005, redBottomZ);
    const redBottomRight = new THREE.Vector3(rightCol, 0.005, redBottomZ);
    
    const diag3 = new THREE.BufferGeometry().setFromPoints([redTopLeft, redBottomRight]);
    const diag4 = new THREE.BufferGeometry().setFromPoints([redTopRight, redBottomLeft]);
    this.boardGroup.add(new THREE.Line(diag3, material));
    this.boardGroup.add(new THREE.Line(diag4, material));
    
    // 黑方九宫
    const blackTopZ = (4.5 - 7) * cellSize;
    const blackBottomZ = (4.5 - 9) * cellSize;
    
    const blackTopLeft = new THREE.Vector3(leftCol, 0.005, blackTopZ);
    const blackTopRight = new THREE.Vector3(rightCol, 0.005, blackTopZ);
    const blackBottomLeft = new THREE.Vector3(leftCol, 0.005, blackBottomZ);
    const blackBottomRight = new THREE.Vector3(rightCol, 0.005, blackBottomZ);
    
    const diag1 = new THREE.BufferGeometry().setFromPoints([blackTopLeft, blackBottomRight]);
    const diag2 = new THREE.BufferGeometry().setFromPoints([blackTopRight, blackBottomLeft]);
    this.boardGroup.add(new THREE.Line(diag1, material));
    this.boardGroup.add(new THREE.Line(diag2, material));
  }

  /**
   * 创建楚河汉界文字
   */
  _createRiverLabels() {
    const { colors } = BOARD_CONFIG;
    
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    
    ctx.clearRect(0, 0, 512, 128);
    
    ctx.font = 'bold 80px "KaiTi", "STKaiti", "楷体", "SimSun", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    const riverColorHex = colors.river.toString(16).padStart(6, '0');
    ctx.fillStyle = '#' + riverColorHex;
    ctx.fillText('楚河', 140, 64);
    ctx.fillText('汉界', 380, 64);
    
    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    
    const material = new THREE.MeshBasicMaterial({ 
      map: texture, 
      transparent: true,
      opacity: 1.0,
      side: THREE.DoubleSide
    });
    
    const geometry = new THREE.PlaneGeometry(3.2, 0.8);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.set(0, 0.008, 0);
    
    this.boardGroup.add(mesh);
  }

  /**
   * 创建程序化棋子
   */
  createPiece(pieceChar, iccs) {
    const color = pieceChar === pieceChar.toUpperCase() ? 'red' : 'black';
    const colors = PIECE_CONFIG.colors[color];
    const config = PIECE_CONFIG;
    
    const group = new THREE.Group();
    
    // 底座 - 使用 StandardMaterial
    const baseGeometry = new THREE.CylinderGeometry(config.radius, config.radius + 0.02, 0.08, 32);
    const baseMaterial = new THREE.MeshStandardMaterial({
      color: colors.base,
      roughness: 0.4,
      metalness: 0.1,
    });
    const base = new THREE.Mesh(baseGeometry, baseMaterial);
    base.castShadow = true;
    base.receiveShadow = true;
    group.add(base);
    
    // 主体 - 使用 StandardMaterial
    const bodyGeometry = new THREE.CylinderGeometry(config.radius - 0.02, config.radius, config.height - 0.1, 32);
    const bodyMaterial = new THREE.MeshStandardMaterial({
      color: colors.body,
      roughness: 0.3,
      metalness: 0.0,
    });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.y = config.height / 2;
    body.castShadow = true;
    body.receiveShadow = true;
    group.add(body);
    
    // 文字
    const textMesh = this._createPieceText(pieceChar, colors.text);
    textMesh.position.y = config.height + 0.01;
    group.add(textMesh);
    
    // 设置位置
    const pos = this._iccsToWorld(iccs);
    group.position.set(pos.x, pos.y, pos.z);
    
    // 黑方棋子旋转180度
    if (color === 'black') {
      group.rotation.y = Math.PI;
    }
    
    group.userData = { iccs, piece: pieceChar };
    this.pieces.set(iccs, group);
    this.piecesGroup.add(group);
    
    // 出现动画
    if (this.animator) {
      this.animator.animateAppear(group);
    }
    
    return group;
  }

  /**
   * 创建棋子文字
   */
  _createPieceText(char, color) {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    
    ctx.clearRect(0, 0, 128, 128);
    
    ctx.fillStyle = '#' + color.toString(16).padStart(6, '0');
    ctx.font = 'bold 80px "Microsoft YaHei", "SimHei", serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this._getPieceDisplayChar(char), 64, 64);
    
    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      side: THREE.DoubleSide,
    });
    
    const geometry = new THREE.PlaneGeometry(0.6, 0.6);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.rotation.x = -Math.PI / 2;
    
    return mesh;
  }

  /**
   * 获取棋子显示字符
   */
  _getPieceDisplayChar(char) {
    const names = {
      'K': '帅', 'A': '仕', 'B': '相', 'N': '傌', 'R': '俥', 'C': '炮', 'P': '兵',
      'k': '将', 'a': '士', 'b': '象', 'n': '马', 'r': '车', 'c': '砲', 'p': '卒',
    };
    return names[char] || char;
  }

  /**
   * ICCS 转世界坐标
   */
  _iccsToWorld(iccs) {
    const col = iccs[0].toLowerCase();
    const row = parseInt(iccs.slice(1));
    
    const colIndex = col.charCodeAt(0) - 'a'.charCodeAt(0);
    const { cellSize } = BOARD_CONFIG;
    
    return {
      x: (colIndex - 4) * cellSize,
      y: 0.04,
      z: (4.5 - row) * cellSize,
    };
  }

  /**
   * 移动棋子
   */
  async movePiece(fromIccs, toIccs, duration = 0.5, isCapture = false) {
    const piece = this.pieces.get(fromIccs);
    if (!piece) {
      console.warn('[Scene] Piece not found at', fromIccs);
      return;
    }
    
    if (this.selectedPiece === fromIccs) {
      this.deselectPiece();
    }
    
    const fromPos = this._iccsToWorld(fromIccs);
    const targetPos = this._iccsToWorld(toIccs);
    
    if (this.particles) {
      this.particles.createTrail(fromPos, targetPos);
    }
    
    if (this.sounds) {
      this.sounds.playMove();
    }
    
    const capturedPiece = this.pieces.get(toIccs);
    if (capturedPiece) {
      await this.removePiece(toIccs, duration * 0.8);
      isCapture = true;
    }
    
    this.pieces.delete(fromIccs);
    this.pieces.set(toIccs, piece);
    piece.userData.iccs = toIccs;
    
    if (this.animator) {
      await this.animator.animateMove(piece, targetPos, {
        duration,
        arcHeight: 0.3,
      });
    } else {
      piece.position.set(targetPos.x, targetPos.y, targetPos.z);
    }
  }

  /**
   * 移除棋子
   */
  async removePiece(iccs, duration = 0.3) {
    const piece = this.pieces.get(iccs);
    if (!piece) return;
    
    this.pieces.delete(iccs);
    const pos = piece.position.clone();
    
    if (this.sounds) {
      this.sounds.playCapture();
    }
    
    if (this.particles) {
      const color = piece.userData.piece === piece.userData.piece.toUpperCase() 
        ? 0xff6b6b 
        : 0x4a4a4a;
      this.particles.createExplosion(pos, color);
    }
    
    if (this.animator) {
      await this.animator.animateCapture(piece, { duration });
    }
    
    this.piecesGroup.remove(piece);
    piece.traverse(child => {
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose());
        } else {
          child.material.dispose();
        }
      }
    });
  }

  /**
   * 选中棋子
   */
  selectPiece(iccs) {
    if (this.selectedPiece === iccs) {
      this.deselectPiece();
      return;
    }

    this.deselectPiece();
    const piece = this.pieces.get(iccs);
    if (!piece) return;

    this.selectedPiece = iccs;
    this._createSelectionHighlight(iccs);
  }

  /**
   * 取消选中
   */
  deselectPiece() {
    if (this._selectionAnimationId !== null && this.animator) {
      this.animator.stopAnimation(this._selectionAnimationId);
      this._selectionAnimationId = null;
    }

    if (this._selectionHighlight) {
      this.effectsGroup.remove(this._selectionHighlight);
      this._selectionHighlight.geometry.dispose();
      this._selectionHighlight.material.dispose();
      this._selectionHighlight = null;
    }

    this.selectedPiece = null;
  }

  /**
   * 创建选中高亮
   */
  _createSelectionHighlight(iccs) {
    const pos = this._iccsToWorld(iccs);

    const geometry = new THREE.RingGeometry(0.4, 0.5, 32);
    const material = new THREE.MeshBasicMaterial({
      color: 0xffd700,
      transparent: true,
      opacity: 0.8,
      side: THREE.DoubleSide,
    });

    this._selectionHighlight = new THREE.Mesh(geometry, material);
    this._selectionHighlight.rotation.x = -Math.PI / 2;
    this._selectionHighlight.position.set(pos.x, 0.06, pos.z);

    this.effectsGroup.add(this._selectionHighlight);

    if (this.animator) {
      this._selectionAnimationId = this.animator.animateSelection(this._selectionHighlight);
    }
  }

  /**
   * 高亮最后走法
   */
  highlightLastMove(fromIccs, toIccs) {
    this.clearHighlights();
    this._createHighlightMarker(fromIccs, 0x00ff00, 'from');
    this._createHighlightMarker(toIccs, 0x0088ff, 'to');
  }

  /**
   * 创建高亮标记
   */
  _createHighlightMarker(iccs, color, type) {
    const pos = this._iccsToWorld(iccs);
    
    const geometry = new THREE.RingGeometry(0.35, 0.45, 32);
    const material = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.6,
      side: THREE.DoubleSide,
    });
    
    const marker = new THREE.Mesh(geometry, material);
    marker.rotation.x = -Math.PI / 2;
    marker.position.set(pos.x, 0.05, pos.z);
    marker.userData = { type: 'highlight', highlightType: type };
    
    this.effectsGroup.add(marker);
    
    // 呼吸动画
    const animate = () => {
      if (!marker.parent) return;
      const time = performance.now() / 1000;
      const scale = 1 + Math.sin(time * 3) * 0.1;
      marker.scale.setScalar(scale);
      marker.material.opacity = 0.4 + Math.sin(time * 3) * 0.2;
      marker._animFrameId = requestAnimationFrame(animate);
    };
    marker._animFrameId = requestAnimationFrame(animate);
  }

  /**
   * 清除高亮
   */
  clearHighlights() {
    const toRemove = [];
    this.effectsGroup.traverse(child => {
      if (child.userData && child.userData.type === 'highlight') {
        if (child._animFrameId) {
          cancelAnimationFrame(child._animFrameId);
        }
        toRemove.push(child);
      }
    });
    toRemove.forEach(obj => this.effectsGroup.remove(obj));
  }

  /**
   * 更新棋盘布局
   */
  updateBoard(layout) {
    this.pieces.forEach(piece => this.piecesGroup.remove(piece));
    this.pieces.clear();
    
    layout.forEach(({ position, piece }) => {
      this.createPiece(piece, position);
    });
  }

  /**
   * 处理窗口大小变化
   */
  _handleResize() {
    if (!this.camera || !this.renderer) return;
    
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    
    this.renderer.setSize(width, height);
  }

  /**
   * 开始渲染循环
   */
  _startRenderLoop() {
    this._isRunning = true;
    this._lastTime = performance.now();
    
    const render = (time) => {
      if (!this._isRunning) return;
      
      this._animationId = requestAnimationFrame(render);
      
      const deltaTime = Math.min((time - this._lastTime) / 1000, 0.1);
      this._lastTime = time;
      
      if (this.controls) {
        this.controls.update();
      }
      
      if (this.particles) {
        this.particles.update(deltaTime);
      }
      
      this.renderer.render(this.scene, this.camera);
    };
    
    render(performance.now());
  }

  /**
   * 动画移动相机
   */
  animateCamera(targetPos, lookAt, duration = 1.0) {
    return new Promise((resolve) => {
      const startPos = this.camera.position.clone();
      const startLookAt = this.controls.target.clone();
      const startTime = performance.now();
      
      this.controls.enabled = false;
      
      const easeOutCubic = t => 1 - Math.pow(1 - t, 3);
      
      const animate = (time) => {
        const elapsed = (time - startTime) / 1000;
        const progress = Math.min(elapsed / duration, 1);
        const eased = easeOutCubic(progress);
        
        this.camera.position.x = startPos.x + (targetPos.x - startPos.x) * eased;
        this.camera.position.y = startPos.y + (targetPos.y - startPos.y) * eased;
        this.camera.position.z = startPos.z + (targetPos.z - startPos.z) * eased;
        
        this.controls.target.x = startLookAt.x + (lookAt.x - startLookAt.x) * eased;
        this.controls.target.y = startLookAt.y + (lookAt.y - startLookAt.y) * eased;
        this.controls.target.z = startLookAt.z + (lookAt.z - startLookAt.z) * eased;
        
        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          this.controls.enabled = true;
          resolve();
        }
      };
      
      requestAnimationFrame(animate);
    });
  }

  /**
   * 重置相机到默认位置
   */
  resetCamera(duration = 1.0) {
    const [x, y, z] = this.options.cameraPosition;
    return this.animateCamera({ x, y, z }, { x: 0, y: 0, z: 0 }, duration);
  }

  /**
   * 停止渲染
   */
  stop() {
    this._isRunning = false;
    if (this._animationId) {
      cancelAnimationFrame(this._animationId);
    }
  }

  /**
   * 显示将军效果
   */
  showCheck(kingIccs) {
    if (this.sounds) {
      this.sounds.playCheck();
    }
    
    if (this.particles && kingIccs) {
      const pos = this._iccsToWorld(kingIccs);
      this.particles.createCheckWarning(pos);
    }
    
    const king = this.pieces.get(kingIccs);
    if (king) {
      if (!king.userData.originalMaterials) {
        king.userData.originalMaterials = [];
        king.traverse((child) => {
          if (child.material) {
            king.userData.originalMaterials.push(child.material.clone());
          }
        });
      }
      
      let flashCount = 0;
      const maxFlashes = 6;
      const flashInterval = setInterval(() => {
        king.traverse((child) => {
          if (child.material && child.material.emissive) {
            if (flashCount % 2 === 0) {
              child.material.emissive.setHex(0xff0000);
              child.material.emissiveIntensity = 0.5;
            } else {
              child.material.emissive.setHex(0x000000);
              child.material.emissiveIntensity = 0;
            }
          }
        });
        
        flashCount++;
        if (flashCount >= maxFlashes) {
          clearInterval(flashInterval);
          king.traverse((child) => {
            if (child.material) {
              child.material.emissive.setHex(0x000000);
              child.material.emissiveIntensity = 0;
            }
          });
        }
      }, 200);
    }
  }

  /**
   * 销毁场景
   */
  dispose() {
    this.stop();
    
    if (this.animator) {
      this.animator.stopAll();
    }
    
    if (this.particles) {
      this.particles.clear();
    }
    
    if (this._resizeHandler) {
      window.removeEventListener('resize', this._resizeHandler);
    }
    
    if (this.renderer) {
      this.renderer.dispose();
    }
    
    if (this.controls) {
      this.controls.dispose();
    }
  }
}

// 导出到全局
window.SceneManager = SceneManager;
window.RENDERER_TYPE = RENDERER_TYPE;
window.BOARD_CONFIG = BOARD_CONFIG;
window.PIECE_CONFIG = PIECE_CONFIG;
