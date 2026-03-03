// ============================================================
// MATRIX CODE RAIN ANIMATION
// Creates the iconic falling green characters background effect
// ============================================================

class MatrixRain {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.drops = [];
    this.characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()_+-=[]{}|;:,.<>?";
    this.matrixCharacters = "ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ";
    this.allChars = this.characters + this.matrixCharacters;
    this.isInitialized = false;
    this.isPaused = false;
    this.animationFrameId = null;
  }

  init() {
    if (this.isInitialized) return;
    
    // Create canvas element
    this.canvas = document.createElement('canvas');
    this.canvas.id = 'matrix-canvas';
    this.ctx = this.canvas.getContext('2d');
    
    // Insert canvas as first child of body (behind everything)
    document.body.insertBefore(this.canvas, document.body.firstChild);
    
    // Set up canvas
    this.resizeCanvas();
    this.initDrops();
    
    // Start animation
    this.animate();
    
    // Handle window resize
    window.addEventListener('resize', () => this.resizeCanvas());
    
    this.isInitialized = true;
    console.log('[Matrix] Code rain initialized');
  }

  resizeCanvas() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
    
    // Reinitialize drops after resize  
    this.initDrops();
  }

  initDrops() {
    const columns = Math.floor(this.canvas.width / 20); // 20px wide columns
    this.drops = [];
    
    for (let i = 0; i < columns; i++) {
      this.drops[i] = {
        y: Math.random() * this.canvas.height,
        speed: Math.random() * 3 + 0.5, // Random speed between 0.5-3.5
        length: Math.random() * 20 + 10, // Trail length 10-30 chars
        chars: []
      };
      
      // Initialize character trail for each drop
      for (let j = 0; j < this.drops[i].length; j++) {
        this.drops[i].chars[j] = this.getRandomChar();
      }
    }
  }

  getRandomChar() {
    return this.allChars[Math.floor(Math.random() * this.allChars.length)];
  }

  animate() {
    if (this.isPaused) {
      this.animationFrameId = null;
      return;
    }

    // Subtle black overlay to create trail effect
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Set text properties
    this.ctx.font = '14px monospace';
    this.ctx.textAlign = 'center';
    
    // Draw each column
    for (let i = 0; i < this.drops.length; i++) {
      const drop = this.drops[i];
      const x = i * 20;
      
      // Draw each character in the trail
      for (let j = 0; j < drop.chars.length; j++) {
        const y = drop.y - (j * 20);
        
        if (y > this.canvas.height) continue;
        if (y < -20) continue;
        
        // Color gradient - brighter at front, dimmer towards back
        const alpha = (drop.chars.length - j) / drop.chars.length;
        const brightness = Math.floor(100 + (155 * alpha));
        
        if (j === 0) {
          // Leading character - bright white/green
          this.ctx.fillStyle = `rgb(${brightness}, 255, ${brightness})`;
        } else if (j < 3) {
          // Next few characters - bright green
          this.ctx.fillStyle = `rgba(0, 255, 65, ${alpha})`;
        } else {
          // Trailing characters - darker green
          this.ctx.fillStyle = `rgba(0, ${brightness}, 17, ${alpha * 0.8})`;
        }
        
        // Add slight glow effect for leading characters
        if (j < 2) {
          this.ctx.shadowColor = '#00ff41';
          this.ctx.shadowBlur = 3;
        } else {
          this.ctx.shadowBlur = 0;
        }
        
        this.ctx.fillText(drop.chars[j], x, y);
      }
      
      // Move drop down
      drop.y += drop.speed;
      
      // Reset drop if it goes off screen
      if (drop.y - (drop.length * 20) > this.canvas.height) {
        drop.y = -drop.length * 20;
        drop.speed = Math.random() * 3 + 0.5;
        
        // Occasionally change characters in the trail
        if (Math.random() < 0.1) {
          for (let j = 0; j < drop.chars.length; j++) {
            drop.chars[j] = this.getRandomChar();
          }
        }
      }
      
      // Occasionally update characters in moving drops
      if (Math.random() < 0.02) {
        const randomIndex = Math.floor(Math.random() * drop.chars.length);
        drop.chars[randomIndex] = this.getRandomChar();
      }
    }
    
    // Reset shadow for next frame
    this.ctx.shadowBlur = 0;
    
    // Continue animation
    this.animationFrameId = requestAnimationFrame(() => this.animate());
  }

  // Method to pause/resume animation (for performance)
  pause() {
    this.isPaused = true;
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  resume() {
    if (!this.isPaused) return;
    this.isPaused = false;
    this.animate();
  }
}

// Initialize Matrix Rain when DOM is loaded
let matrixRain;

function initializeMatrix() {
  matrixRain = new MatrixRain();
  matrixRain.init();
}

// Auto-start when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeMatrix);
} else {
  initializeMatrix();
}

// Pause animation when tab is not visible (performance optimization)
document.addEventListener('visibilitychange', () => {
  if (matrixRain) {
    if (document.hidden) {
      matrixRain.pause();
    } else {
      matrixRain.resume();
    }
  }
});

// Export for manual control if needed
window.getMatrixRain = () => matrixRain;