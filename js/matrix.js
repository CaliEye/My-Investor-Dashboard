// ============================================================
// ENHANCED MATRIX CODE RAIN ANIMATION
// Full-screen background effect with dynamic performance optimization
// ============================================================

class MatrixRain {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.drops = [];
    this.fontSize = 14;
    this.columns = 0;
    
    // Character sets for authentic Matrix look
    this.matrixChars = "ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ日本語";
    this.alphaChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    this.symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?/~`";
    this.allChars = this.matrixChars + this.alphaChars + this.symbols;
    
    // Performance and visual settings
    this.isInitialized = false;
    this.isPaused = false;
    this.animationFrameId = null;
    this.lastTime = 0;
    this.targetFPS = 30; // Smooth but not resource-heavy
    this.frameInterval = 1000 / this.targetFPS;
    
    // Dynamic performance adjustment
    this.performanceMode = 'auto'; // auto, high, low
    this.frameCount = 0;
    this.fpsCheckInterval = 60; // Check every 60 frames
    
    // Visual customization
    this.primaryColor = 'rgba(0, 255, 120, 0.8)';
    this.secondaryColor = 'rgba(0, 255, 120, 0.3)';
    this.fadeColor = 'rgba(4, 6, 7, 0.05)';
  }

  init() {
    if (this.isInitialized) return;
    
    console.log('[Matrix] Initializing full-screen code rain...');
    
    // Create canvas element
    this.canvas = document.createElement('canvas');
    this.canvas.id = 'matrix-canvas';
    this.ctx = this.canvas.getContext('2d');
    
    // Set canvas styles for full-screen background
    this.canvas.style.position = 'fixed';
    this.canvas.style.top = '0';
    this.canvas.style.left = '0';
    this.canvas.style.width = '100vw';
    this.canvas.style.height = '100vh';
    this.canvas.style.zIndex = '-10';
    this.canvas.style.pointerEvents = 'none';
    this.canvas.style.opacity = 'var(--rain-opacity, 0.2)';
    
    // Insert canvas as first child of body (behind everything)
    if (document.body.firstChild) {
      document.body.insertBefore(this.canvas, document.body.firstChild);
    } else {
      document.body.appendChild(this.canvas);
    }
    
    // Set up canvas and initialize
    this.resizeCanvas();
    this.initDrops();
    
    // Event listeners
    window.addEventListener('resize', this.handleResize.bind(this));
    document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    
    // Start animation
    this.animate();
    
    this.isInitialized = true;
    console.log('[Matrix] Code rain initialized - Full screen active');
  }

  handleResize() {
    clearTimeout(this.resizeTimeout);
    this.resizeTimeout = setTimeout(() => {
      this.resizeCanvas();
      this.initDrops();
    }, 250);
  }

  handleVisibilityChange() {
    if (document.hidden) {
      this.pause();
    } else {
      this.resume();
    }
  }

  resizeCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const rect = { width: window.innerWidth, height: window.innerHeight };
    
    // Set actual size in memory (scaled to account for pixel ratio)
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    
    // Scale the drawing context so everything shows up at the right size
    this.ctx.scale(dpr, dpr);
    
    // Set display size (CSS pixels)
    this.canvas.style.width = rect.width + 'px';
    this.canvas.style.height = rect.height + 'px';
    
    // Update column count based on new width
    this.columns = Math.floor(rect.width / this.fontSize);
    
    console.log(`[Matrix] Canvas resized: ${rect.width}x${rect.height}, Columns: ${this.columns}`);
  }

  initDrops() {
    this.drops = [];
    
    for (let i = 0; i < this.columns; i++) {
      this.drops[i] = {
        y: Math.random() * window.innerHeight,
        speed: Math.random() * 2 + 0.5, // Speed between 0.5-2.5
        length: Math.random() * 15 + 8, // Trail length 8-23 chars
        chars: [],
        lastCharChange: 0,
        changeRate: Math.random() * 100 + 50 // Change characters every 50-150 frames
      };
      
      // Initialize character trail for each drop
      for (let j = 0; j < this.drops[i].length; j++) {
        this.drops[i].chars[j] = this.getRandomChar();
      }
    }
    
    console.log(`[Matrix] Initialized ${this.columns} drops`);
  }

  getRandomChar() {
    return this.allChars[Math.floor(Math.random() * this.allChars.length)];
  }

  adjustPerformance() {
    this.frameCount++;
    
    if (this.frameCount % this.fpsCheckInterval === 0) {
      const currentTime = performance.now();
      const frameTime = (currentTime - this.lastFPSCheck) / this.fpsCheckInterval;
      this.lastFPSCheck = currentTime;
      
      // Auto-adjust performance based on frame time
      if (this.performanceMode === 'auto') {
        if (frameTime > 35) { // Running slow
          this.targetFPS = Math.max(15, this.targetFPS - 5);
          this.fadeColor = 'rgba(4, 6, 7, 0.08)'; // Faster fade
        } else if (frameTime < 20) { // Running fast
          this.targetFPS = Math.min(60, this.targetFPS + 5);
          this.fadeColor = 'rgba(4, 6, 7, 0.04)'; // Slower fade
        }
        this.frameInterval = 1000 / this.targetFPS;
      }
    }
  }

  animate(currentTime = 0) {
    if (this.isPaused) {
      this.animationFrameId = null;
      return;
    }

    // Throttle frame rate for performance
    if (currentTime - this.lastTime >= this.frameInterval) {
      this.draw();
      this.lastTime = currentTime;
      this.adjustPerformance();
    }
    
    this.animationFrameId = requestAnimationFrame(this.animate.bind(this));
  }

  draw() {
    // Clear canvas fully — background images show through between characters
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Set text properties
    this.ctx.font = `${this.fontSize}px 'IBM Plex Mono', 'JetBrains Mono', monospace`;
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'top';
    
    // Draw each column
    for (let i = 0; i < this.drops.length; i++) {
      if (i >= this.columns) break; // Safety check
      
      const drop = this.drops[i];
      const x = i * this.fontSize + this.fontSize / 2;
      
      // Update drop position
      drop.y += drop.speed;
      
      // Reset drop when it goes off screen
      if (drop.y > window.innerHeight + drop.length * this.fontSize) {
        drop.y = -drop.length * this.fontSize;
        drop.speed = Math.random() * 2 + 0.5;
        drop.changeRate = Math.random() * 100 + 50;
      }
      
      // Randomly change characters in the trail
      drop.lastCharChange++;
      if (drop.lastCharChange > drop.changeRate) {
        const randomIndex = Math.floor(Math.random() * drop.chars.length);
        drop.chars[randomIndex] = this.getRandomChar();
        drop.lastCharChange = 0;
      }
      
      // Draw each character in the trail
      for (let j = 0; j < drop.chars.length; j++) {
        const y = drop.y - (j * this.fontSize);
        
        // Skip if character is off screen
        if (y > window.innerHeight + this.fontSize || y < -this.fontSize) continue;
        
        // Calculate opacity based on position in trail
        let alpha;
        if (j === 0) {
          // Leading character - brightest
          alpha = 1.0;
          this.ctx.fillStyle = this.primaryColor;
        } else {
          // Trail characters - fade out
          alpha = Math.max(0.1, 1 - (j / drop.length));
          const intensity = Math.floor(255 * alpha * 0.8);
          this.ctx.fillStyle = `rgba(0, ${intensity}, ${Math.floor(intensity * 0.47)}, ${alpha})`;
        }
        
        // Add slight random flicker to leading character
        if (j === 0 && Math.random() > 0.98) {
          this.ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        }
        
        // Draw the character
        this.ctx.fillText(drop.chars[j], x, y);
      }
    }
  }

  pause() {
    this.isPaused = true;
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    console.log('[Matrix] Animation paused');
  }

  resume() {
    if (!this.isPaused) return;
    this.isPaused = false;
    this.animate();
    console.log('[Matrix] Animation resumed');
  }

  destroy() {
    this.pause();
    if (this.canvas && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    window.removeEventListener('resize', this.handleResize.bind(this));
    document.removeEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    this.isInitialized = false;
    console.log('[Matrix] Animation destroyed');
  }

  // Public methods for external control
  setOpacity(opacity) {
    if (this.canvas) {
      this.canvas.style.opacity = opacity;
    }
  }

  setSpeed(multiplier = 1) {
    this.drops.forEach(drop => {
      drop.speed = (Math.random() * 2 + 0.5) * multiplier;
    });
  }

  setDensity(multiplier = 1) {
    const newColumns = Math.floor(this.columns * multiplier);
    if (newColumns !== this.columns) {
      this.columns = newColumns;
      this.initDrops();
    }
  }
}

// ============================================================
// AUTO-INITIALIZATION & PAGE-SPECIFIC CONFIGURATIONS
// ============================================================

// Global matrix instance
let matrixRain = null;

// Initialize when DOM is ready
function initMatrixRain() {
  if (matrixRain) return; // Already initialized
  
  matrixRain = new MatrixRain();
  
  // Apply page-specific configurations
  const body = document.body;
  const pageClass = body.className;
  
  // Configure based on page type
  if (pageClass.includes('macro-page')) {
    matrixRain.setOpacity(0.3);
    matrixRain.setSpeed(0.7); // Slower, more corporate
  } else if (pageClass.includes('bots-page')) {
    matrixRain.setOpacity(0.25);
    matrixRain.setSpeed(1.2); // Faster, more tech
    matrixRain.setDensity(1.1); // Denser
  } else if (pageClass.includes('crypto-page')) {
    matrixRain.setOpacity(0.22);
    matrixRain.setSpeed(1.5); // Fast-moving market feel
  } else if (pageClass.includes('portfolio-page')) {
    matrixRain.setOpacity(0.18);
    matrixRain.setSpeed(0.8); // Calm, steady
  } else if (pageClass.includes('scenario-page')) {
    matrixRain.setOpacity(0.28);
    matrixRain.setSpeed(0.9);
  } else if (pageClass.includes('mindmap-page')) {
    matrixRain.setOpacity(0.12);
    matrixRain.setSpeed(0.6); // Very subtle
    matrixRain.setDensity(0.7); // Less dense
  } else if (pageClass.includes('goals-page')) {
    matrixRain.setOpacity(0.20);
    matrixRain.setSpeed(1.0);
  }
  
  // Initialize the animation
  matrixRain.init();
  
  console.log('[Matrix] Rain configured for page type:', pageClass || 'default');
}

// Initialize immediately if DOM is already loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initMatrixRain);
} else {
  // DOM is already loaded
  setTimeout(initMatrixRain, 100);
}

// Export for external access
if (typeof window !== 'undefined') {
  window.MatrixRain = MatrixRain;
  window.matrixRain = matrixRain;
}

// Debug controls (remove in production)
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  window.matrixDebug = {
    setOpacity: (opacity) => matrixRain?.setOpacity(opacity),
    setSpeed: (multiplier) => matrixRain?.setSpeed(multiplier),
    setDensity: (multiplier) => matrixRain?.setDensity(multiplier),
    pause: () => matrixRain?.pause(),
    resume: () => matrixRain?.resume()
  };
  
  console.log('[Matrix] Debug controls available: window.matrixDebug');
}