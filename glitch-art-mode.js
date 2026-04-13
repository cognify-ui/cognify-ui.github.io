// glitch-art-mode.js
// Художественный глюк — работает на любой странице, независимо от её содержимого

(function() {
    // Режим включен?
    let isGlitchActive = localStorage.getItem('glitchMode') === 'true';
    
    // Создаём переключатель (всегда добавляем в правый нижний угол)
    const addToggleButton = () => {
        const btn = document.createElement('button');
        btn.id = 'glitch-toggle';
        btn.textContent = isGlitchActive ? '🎨 Глюк: ВЫКЛ' : '🎨 Глюк: ВКЛ';
        btn.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 999999;
            background: #000;
            color: #0f0;
            border: 2px solid #0f0;
            padding: 8px 12px;
            cursor: pointer;
            font-family: monospace;
            font-size: 12px;
            border-radius: 4px;
            transition: all 0.2s;
        `;
        btn.onclick = () => {
            isGlitchActive = !isGlitchActive;
            localStorage.setItem('glitchMode', isGlitchActive);
            btn.textContent = isGlitchActive ? '🎨 Глюк: ВЫКЛ' : '🎨 Глюк: ВКЛ';
            if (isGlitchActive) {
                enableGlitch();
            } else {
                disableGlitch();
            }
        };
        document.body.appendChild(btn);
    };
    
    // Добавляем CSS-глюки
    const addGlitchStyles = () => {
        const style = document.createElement('style');
        style.id = 'glitch-styles';
        style.textContent = `
            /* Глюк-эффекты — применяются ко всем элементам, но не ломают функционал */
            .glitch-active button,
            .glitch-active .btn,
            .glitch-active [role="button"] {
                transition: all 0.05s cubic-bezier(0.5, 1.5, 0.5, 0.8) !important;
            }
            
            .glitch-active button:hover {
                transform: translate(2px, -1px) rotate(0.5deg) !important;
            }
            
            @keyframes colorGlitch {
                0% { filter: hue-rotate(0deg); }
                25% { filter: hue-rotate(90deg) invert(0.05); }
                50% { filter: hue-rotate(180deg); }
                75% { filter: hue-rotate(270deg) brightness(1.1); }
                100% { filter: hue-rotate(360deg); }
            }
            
            .glitch-active body {
                animation: colorGlitch 8s infinite;
            }
            
            @keyframes floatGlitch {
                0%, 100% { transform: translate(0, 0); }
                33% { transform: translate(-1px, 1px); }
                66% { transform: translate(1px, -1px); }
            }
            
            .glitch-active input,
            .glitch-active textarea {
                animation: floatGlitch 0.3s infinite;
            }
            
            /* Случайные мерцания */
            .glitch-active .glitch-random {
                animation: randomShake 0.15s infinite;
            }
        `;
        document.head.appendChild(style);
    };
    
    // Основные функции
    const enableGlitch = () => {
        document.body.classList.add('glitch-active');
        startRandomGlitches();
    };
    
    const disableGlitch = () => {
        document.body.classList.remove('glitch-active');
        if (window.randomGlitchInterval) clearInterval(window.randomGlitchInterval);
    };
    
    const startRandomGlitches = () => {
        if (window.randomGlitchInterval) clearInterval(window.randomGlitchInterval);
        window.randomGlitchInterval = setInterval(() => {
            if (!isGlitchActive) return;
            // Случайно выбираем элемент и применяем кратковременный глюк
            const allElements = document.querySelectorAll('button, input, .message, .chat-item');
            if (allElements.length > 0) {
                const randomEl = allElements[Math.floor(Math.random() * allElements.length)];
                randomEl.classList.add('glitch-random');
                setTimeout(() => randomEl.classList.remove('glitch-random'), 200);
            }
        }, 3000);
    };
    
    // Инициализация
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            addGlitchStyles();
            addToggleButton();
            if (isGlitchActive) enableGlitch();
        });
    } else {
        addGlitchStyles();
        addToggleButton();
        if (isGlitchActive) enableGlitch();
    }
})();
