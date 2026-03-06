// ============================================================
// CINEMATIC BACKGROUND MANAGER
// Handles dynamic background switching and atmospheric effects
// ============================================================

class CinematicBackgroundManager {
  constructor() {
    this.backgrounds = {
      'macro-page': {
        image: 'images/lab.jpg',
        overlay: 'rgba(0, 40, 80, 0.75)',
        atmosphere: 'corporate'
      },
      'bots-page': {
        image: 'images/hud55.jpg',
        overlay: 'rgba(0, 20, 40, 0.80)',
        atmosphere: 'technical'
      },
      'crypto-page': {
        image: 'images/outsidecool.jpg',
        overlay: 'rgba(0, 30, 60, 0.85)',
        atmosphere: 'dynamic'
      },
      'portfolio-page': {
        image: 'images/hallway.jpg',
        overlay: 'rgba(0, 25, 50, 0.75)',
        atmosphere: 'stable'
      },
      'scenario-page': {
        image: 'images/bar.jpg',
        overlay: 'rgba(40, 20, 0, 0.70)',
        atmosphere: 'alert'
      },
      'mindmap-page': {
        image: 'images/green simple.jpg',
        overlay: 'rgba(0, 20, 20, 0.60)',
        atmosphere: 'focus'
      },
      'goals-page': {
        image: 'images/lab.jpg',
        overlay: 'rgba(0, 30, 30, 0.70)',
        atmosphere: 'motivational'
      },
      'warroom-page': {
        image: 'images/hud2.jpg',
        overlay: 'rgba(20, 0, 0, 0.75)',
        atmosphere: 'alert'
      },
      'insights-page': {
        image: 'images/hud3.jpg',
        overlay: 'rgba(0, 20, 40, 0.80)',
        atmosphere: 'corporate'
      },
      'sentiment-page': {
        image: 'images/hud4.jpg',
        overlay: 'rgba(0, 30, 60, 0.80)',
        atmosphere: 'dynamic'
      },
      'links-page': {
        image: 'images/outsidecool.jpg',
        overlay: 'rgba(0, 20, 40, 0.75)',
        atmosphere: 'focus'
      },
      'fortress-page': {
        image: 'images/hud55.jpg',
        overlay: 'rgba(0, 10, 20, 0.82)',
        atmosphere: 'technical'
      }
    };
    
    this.isInitialized = false;
    this.currentBackground = null;
    this.atmosphereAnimations = [];
  }

  init() {
    if (this.isInitialized) return;
    
    console.log('[Cinematic] Initializing background system...');
    
    // Create background container
    this.createBackgroundContainer();
    
    // Detect current page type
    const pageType = this.detectPageType();
    
    // Set appropriate background
    this.setBackground(pageType);
    
    // Initialize atmospheric effects
    this.initAtmosphereEffects(pageType);

    // Initialize parallax effect
    this.initParallax();

    this.isInitialized = true;
    console.log(`[Cinematic] Background system active for: ${pageType}`);
  }

  detectPageType() {
    const body = document.body;
    const classes = ['macro-page', 'bots-page', 'crypto-page', 'portfolio-page',
                    'scenario-page', 'mindmap-page', 'goals-page',
                    'warroom-page', 'insights-page', 'sentiment-page',
                    'links-page', 'fortress-page'];
    
    for (const className of classes) {
      if (body.classList.contains(className)) {
        return className;
      }
    }
    
    return 'macro-page'; // default
  }

  createBackgroundContainer() {
    // Remove existing background if present
    const existing = document.getElementById('cinematic-background');
    if (existing) existing.remove();
    
    // Create new background container
    const container = document.createElement('div');
    container.id = 'cinematic-background';
    container.className = 'cinematic-background';
    
    // Insert as first child of body
    document.body.insertBefore(container, document.body.firstChild);
    
    this.backgroundContainer = container;
  }

  setBackground(pageType) {
    if (!this.backgrounds[pageType]) {
      console.warn(`[Cinematic] No background defined for: ${pageType}`);
      return;
    }
    
    const config = this.backgrounds[pageType];
    this.currentBackground = config;
    
    // Set background image with overlay
    this.backgroundContainer.style.backgroundImage = `
      linear-gradient(${config.overlay}, ${config.overlay}),
      url('${config.image}')
    `;
    this.backgroundContainer.style.backgroundSize = 'cover';
    this.backgroundContainer.style.backgroundPosition = 'center';
    this.backgroundContainer.style.backgroundAttachment = 'fixed';
    
    // Add page-specific class for additional styling
    this.backgroundContainer.className = `cinematic-background atmosphere-${config.atmosphere}`;
    
    console.log(`[Cinematic] Background set: ${config.image} with ${config.atmosphere} atmosphere`);
  }

  initAtmosphereEffects(pageType) {
    // Clear existing effects
    this.clearAtmosphereEffects();
    
    const config = this.backgrounds[pageType];
    if (!config) return;
    
    switch (config.atmosphere) {
      case 'corporate':
        this.addCorporateEffects();
        break;
      case 'technical':
        this.addTechnicalEffects();
        break;
      case 'dynamic':
        this.addDynamicEffects();
        break;
      case 'stable':
        this.addStableEffects();
        break;
      case 'alert':
        this.addAlertEffects();
        break;
      case 'focus':
        this.addFocusEffects();
        break;
      case 'motivational':
        this.addMotivationalEffects();
        break;
    }
  }

  addCorporateEffects() {
    // Subtle gold accent highlights
    this.addFloatingParticles(3, '#FFD166', 0.3);
  }

  addTechnicalEffects() {
    // Matrix-style data streams
    this.addDataStreams(5, '#00FF78', 0.4);
  }

  addDynamicEffects() {
    // Electric blue energy pulses
    this.addEnergyPulses(4, '#00D2FF', 0.5);
  }

  addStableEffects() {
    // Gentle green glow waves
    this.addGlowWaves(2, '#2ED573', 0.25);
  }

  addAlertEffects() {
    // Warning color shifts
    this.addColorShifts(['#FFD166', '#FF4757'], 0.3);
  }

  addFocusEffects() {
    // Minimal green accents
    this.addMinimalAccents('#00FF78', 0.2);
  }

  addMotivationalEffects() {
    // Success-oriented green highlights
    this.addSuccessHighlights('#2ED573', 0.35);
  }

  addFloatingParticles(count, color, opacity) {
    for (let i = 0; i < count; i++) {
      const particle = document.createElement('div');
      particle.className = 'floating-particle';
      particle.style.cssText = `
        position: absolute;
        width: 2px;
        height: 2px;
        background: ${color};
        border-radius: 50%;
        opacity: ${opacity};
        animation: floatParticle ${8 + Math.random() * 4}s linear infinite;
        left: ${Math.random() * 100}%;
        top: ${Math.random() * 100}%;
        box-shadow: 0 0 4px ${color};
      `;
      
      this.backgroundContainer.appendChild(particle);
      this.atmosphereAnimations.push(particle);
    }
  }

  addDataStreams(count, color, opacity) {
    // Implementation for technical data stream effects
    for (let i = 0; i < count; i++) {
      const stream = document.createElement('div');
      stream.className = 'data-stream';
      stream.style.cssText = `
        position: absolute;
        width: 1px;
        height: 20px;
        background: linear-gradient(transparent, ${color}, transparent);
        opacity: ${opacity};
        animation: dataStream ${3 + Math.random() * 2}s linear infinite;
        left: ${Math.random() * 100}%;
        top: -20px;
      `;
      
      this.backgroundContainer.appendChild(stream);
      this.atmosphereAnimations.push(stream);
    }
  }

  addEnergyPulses(count, color, opacity) {
    // Electric energy pulse effects
    for (let i = 0; i < count; i++) {
      const pulse = document.createElement('div');
      pulse.className = 'energy-pulse';
      pulse.style.cssText = `
        position: absolute;
        width: 30px;
        height: 30px;
        border: 1px solid ${color};
        border-radius: 50%;
        opacity: ${opacity};
        animation: energyPulse ${4 + Math.random() * 2}s ease-in-out infinite;
        left: ${Math.random() * 100}%;
        top: ${Math.random() * 100}%;
      `;
      
      this.backgroundContainer.appendChild(pulse);
      this.atmosphereAnimations.push(pulse);
    }
  }

  addGlowWaves(count, color, opacity) {
    // Gentle glow wave effects
    const wave = document.createElement('div');
    wave.className = 'glow-wave';
    wave.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: radial-gradient(ellipse at center, transparent 40%, ${color} 70%, transparent 100%);
      opacity: ${opacity};
      animation: glowWave 8s ease-in-out infinite alternate;
    `;
    
    this.backgroundContainer.appendChild(wave);
    this.atmosphereAnimations.push(wave);
  }

  addColorShifts(colors, opacity) {
    // Color shifting background overlay
    const shift = document.createElement('div');
    shift.className = 'color-shift';
    shift.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      opacity: ${opacity};
      animation: colorShift 6s ease-in-out infinite alternate;
    `;
    
    // Create CSS animation for color shifts
    const style = document.createElement('style');
    style.textContent = `
      @keyframes colorShift {
        0% { background: radial-gradient(circle, ${colors[0]}20, transparent); }
        100% { background: radial-gradient(circle, ${colors[1]}20, transparent); }
      }
    `;
    document.head.appendChild(style);
    
    this.backgroundContainer.appendChild(shift);
    this.atmosphereAnimations.push(shift);
  }

  addMinimalAccents(color, opacity) {
    // Minimal accent effects for focus mode
    const accent = document.createElement('div');
    accent.className = 'minimal-accent';
    accent.style.cssText = `
      position: absolute;
      top: 20%;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(90deg, transparent, ${color}, transparent);
      opacity: ${opacity};
      animation: minimalPulse 10s ease-in-out infinite;
    `;
    
    this.backgroundContainer.appendChild(accent);
    this.atmosphereAnimations.push(accent);
  }

  initParallax() {
    document.addEventListener('mousemove', (e) => {
      if (!this.backgroundContainer) return;
      const x = (e.clientX / window.innerWidth - 0.5) * 20;
      const y = (e.clientY / window.innerHeight - 0.5) * 20;
      this.backgroundContainer.style.backgroundPosition =
        `calc(50% + ${x}px) calc(50% + ${y}px)`;
    });
  }

  addSuccessHighlights(color, opacity) {
    // Success-oriented highlighting
    this.addGlowWaves(1, color, opacity);
    this.addFloatingParticles(2, color, opacity * 0.5);
  }

  clearAtmosphereEffects() {
    this.atmosphereAnimations.forEach(element => {
      if (element.parentNode) {
        element.parentNode.removeChild(element);
      }
    });
    this.atmosphereAnimations = [];
  }

  // Public methods for external control
  switchBackground(pageType) {
    if (this.backgrounds[pageType]) {
      this.setBackground(pageType);
      this.initAtmosphereEffects(pageType);
    }
  }

  setOpacity(opacity) {
    if (this.backgroundContainer) {
      this.backgroundContainer.style.opacity = opacity;
    }
  }

  destroy() {
    this.clearAtmosphereEffects();
    if (this.backgroundContainer && this.backgroundContainer.parentNode) {
      this.backgroundContainer.parentNode.removeChild(this.backgroundContainer);
    }
    this.isInitialized = false;
  }
}

// ============================================================
// CSS ANIMATIONS FOR ATMOSPHERIC EFFECTS
// ============================================================

// Add required CSS animations
const cinematicStyles = document.createElement('style');
cinematicStyles.textContent = `
  @keyframes floatParticle {
    0% { transform: translateY(100vh) rotate(0deg); }
    100% { transform: translateY(-20vh) rotate(360deg); }
  }
  
  @keyframes dataStream {
    0% { transform: translateY(-20px); opacity: 0; }
    10% { opacity: 1; }
    90% { opacity: 1; }
    100% { transform: translateY(100vh); opacity: 0; }
  }
  
  @keyframes energyPulse {
    0% { transform: scale(0.5); opacity: 1; }
    50% { transform: scale(1.2); opacity: 0.5; }
    100% { transform: scale(0.5); opacity: 1; }
  }
  
  @keyframes glowWave {
    0% { transform: scale(0.8) rotate(0deg); }
    100% { transform: scale(1.2) rotate(5deg); }
  }
  
  @keyframes minimalPulse {
    0%, 100% { opacity: 0.1; }
    50% { opacity: 0.4; }
  }
`;
document.head.appendChild(cinematicStyles);

// ============================================================
// AUTO-INITIALIZATION
// ============================================================

let cinematicBackgroundManager = null;

function initCinematicBackground() {
  if (cinematicBackgroundManager) return;
  
  cinematicBackgroundManager = new CinematicBackgroundManager();
  cinematicBackgroundManager.init();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCinematicBackground);
} else {
  setTimeout(initCinematicBackground, 50);
}

// Export for external access
if (typeof window !== 'undefined') {
  window.CinematicBackgroundManager = CinematicBackgroundManager;
  window.cinematicBackgroundManager = cinematicBackgroundManager;
}