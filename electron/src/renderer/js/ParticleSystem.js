/**
 * 粒子系统
 * 
 * 功能:
 * - 移动轨迹粒子
 * - 爆炸效果
 * - 将军警告
 */

// 粒子配置
const PARTICLE_CONFIG = {
  trail: { count: 20, color: 0xffd700, lifetime: 0.5 },
  explosion: { count: 50, color: 0xff6b6b, lifetime: 0.8 },
  checkWarning: { count: 30, color: 0xff0000, lifetime: 1.0 }
};

class ParticleSystem {
  constructor(scene) {
    this.scene = scene;
    this.particles = [];
    this.geometry = null;
    this.material = null;
    this.points = null;
    this.particlePool = [];
    this.maxParticles = 200;
    
    this._init();
  }

  _init() {
    // 创建粒子几何体
    this.geometry = new THREE.BufferGeometry();
    this.geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(this.maxParticles * 3), 3));
    this.geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(this.maxParticles * 3), 3));
    this.geometry.setAttribute('size', new THREE.BufferAttribute(new Float32Array(this.maxParticles), 1));
    this.geometry.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array(this.maxParticles), 1));
    
    // 创建着色器材质
    this.material = new THREE.ShaderMaterial({
      uniforms: {},
      vertexShader: `
        attribute float size;
        attribute float alpha;
        attribute vec3 color;
        varying vec3 vColor;
        varying float vAlpha;
        
        void main() {
          vColor = color;
          vAlpha = alpha;
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * (300.0 / -mvPosition.z);
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        varying float vAlpha;
        
        void main() {
          float r = distance(gl_PointCoord, vec2(0.5));
          if (r > 0.5) discard;
          float strength = 1.0 - (r / 0.5);
          gl_FragColor = vec4(vColor, strength * vAlpha);
        }
      `,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    
    this.points = new THREE.Points(this.geometry, this.material);
    this.points.visible = false;
    this.scene.add(this.points);
  }

  /**
   * 创建轨迹粒子
   */
  createTrail(from, to) {
    const count = PARTICLE_CONFIG.trail.count;
    const color = new THREE.Color(PARTICLE_CONFIG.trail.color);
    
    for (let i = 0; i < count; i++) {
      const t = i / count;
      const pos = {
        x: from.x + (to.x - from.x) * t + (Math.random() - 0.5) * 0.2,
        y: from.y + (to.y - from.y) * t + 0.3 + Math.random() * 0.2,
        z: from.z + (to.z - from.z) * t + (Math.random() - 0.5) * 0.2
      };
      
      this._addParticle(pos, color, 0.15, PARTICLE_CONFIG.trail.lifetime);
    }
  }

  /**
   * 创建爆炸效果
   */
  createExplosion(position, colorHex) {
    const count = PARTICLE_CONFIG.explosion.count;
    const color = new THREE.Color(colorHex);
    
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const elevation = (Math.random() - 0.5) * Math.PI;
      const speed = 0.5 + Math.random() * 1.5;
      
      const vel = {
        x: Math.cos(angle) * Math.cos(elevation) * speed,
        y: Math.sin(elevation) * speed + 0.5,
        z: Math.sin(angle) * Math.cos(elevation) * speed
      };
      
      this._addParticle(
        { x: position.x, y: position.y + 0.3, z: position.z },
        color,
        0.1 + Math.random() * 0.15,
        PARTICLE_CONFIG.explosion.lifetime,
        vel
      );
    }
  }

  /**
   * 创建将军警告
   */
  createCheckWarning(position) {
    const count = PARTICLE_CONFIG.checkWarning.count;
    const color = new THREE.Color(PARTICLE_CONFIG.checkWarning.color);
    
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = Math.random() * 0.5;
      const height = Math.random() * 1.0;
      
      this._addParticle(
        {
          x: position.x + Math.cos(angle) * radius,
          y: position.y + 0.3 + height,
          z: position.z + Math.sin(angle) * radius
        },
        color,
        0.1 + Math.random() * 0.1,
        PARTICLE_CONFIG.checkWarning.lifetime,
        { x: 0, y: 0.3, z: 0 }
      );
    }
  }

  /**
   * 添加粒子
   */
  _addParticle(position, color, size, lifetime, velocity = null) {
    // 找到空闲粒子或创建新的
    let particle = this.particlePool.find(p => !p.active);
    
    if (!particle) {
      if (this.particlePool.length >= this.maxParticles) {
        return; // 粒子池已满
      }
      particle = {
        active: false,
        position: new THREE.Vector3(),
        velocity: new THREE.Vector3(),
        color: new THREE.Color(),
        size: 0.1,
        alpha: 1.0,
        lifetime: 0,
        maxLifetime: 1.0
      };
      this.particlePool.push(particle);
    }
    
    particle.active = true;
    particle.position.copy(position);
    particle.velocity.copy(velocity || new THREE.Vector3(0, 0, 0));
    particle.color.copy(color);
    particle.size = size;
    particle.alpha = 1.0;
    particle.lifetime = 0;
    particle.maxLifetime = lifetime;
    
    this.points.visible = true;
  }

  /**
   * 更新粒子
   */
  update(deltaTime) {
    let activeCount = 0;
    const positions = this.geometry.attributes.position.array;
    const colors = this.geometry.attributes.color.array;
    const sizes = this.geometry.attributes.size.array;
    const alphas = this.geometry.attributes.alpha.array;
    
    for (let i = 0; i < this.particlePool.length; i++) {
      const particle = this.particlePool[i];
      
      if (!particle.active) {
        // 隐藏非活跃粒子
        sizes[i] = 0;
        alphas[i] = 0;
        continue;
      }
      
      // 更新生命周期
      particle.lifetime += deltaTime;
      const progress = particle.lifetime / particle.maxLifetime;
      
      if (progress >= 1.0) {
        particle.active = false;
        sizes[i] = 0;
        alphas[i] = 0;
        continue;
      }
      
      // 更新位置
      particle.position.x += particle.velocity.x * deltaTime;
      particle.position.y += particle.velocity.y * deltaTime;
      particle.position.z += particle.velocity.z * deltaTime;
      
      // 重力
      particle.velocity.y -= 2.0 * deltaTime;
      
      // 更新 alpha
      particle.alpha = 1.0 - progress;
      
      // 设置缓冲区数据
      positions[i * 3] = particle.position.x;
      positions[i * 3 + 1] = particle.position.y;
      positions[i * 3 + 2] = particle.position.z;
      
      colors[i * 3] = particle.color.r;
      colors[i * 3 + 1] = particle.color.g;
      colors[i * 3 + 2] = particle.color.b;
      
      sizes[i] = particle.size * (1.0 - progress * 0.5);
      alphas[i] = particle.alpha;
      
      activeCount++;
    }
    
    // 标记属性需要更新
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.attributes.color.needsUpdate = true;
    this.geometry.attributes.size.needsUpdate = true;
    this.geometry.attributes.alpha.needsUpdate = true;
    
    // 如果没有活跃粒子，隐藏点云
    if (activeCount === 0) {
      this.points.visible = false;
    }
  }

  /**
   * 清除所有粒子
   */
  clear() {
    this.particlePool.forEach(particle => {
      particle.active = false;
    });
    this.points.visible = false;
  }
}

// 导出到全局
window.ParticleSystem = ParticleSystem;
window.PARTICLE_CONFIG = PARTICLE_CONFIG;
