/**
 * Spidey Tracker Visual Assets & Interactive Spider-Man Components
 * Inspired by spideytracker.com
 * Includes:
 * 1. Iconic Upside-Down Hanging Spider-Man (with physics web sway & speech bubble)
 * 2. Corner Guardian Spider-Man (with animated Spider-Sense tingle & eye blink)
 * 3. Spider-Web Radar Scanner Widget
 * 4. Classic Spidey Tracker Console Frame & Header Badge
 */

(function () {
    /**
     * SVG for Iconic Hanging Upside-Down Spider-Man
     * Features signature red & blue suit, black web tracery, expressive white eyes with black borders.
     */
    const HANGING_SPIDEY_SVG = `
    <svg viewBox="0 0 120 180" class="hanging-spidey-svg" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <!-- Glowing Web Thread -->
            <filter id="webGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="0" stdDeviation="2" flood-color="#00e5ff" flood-opacity="0.8"/>
            </filter>
            <!-- Spider-Sense Aura -->
            <filter id="senseGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#ff1744" flood-opacity="0.9"/>
            </filter>
        </defs>

        <!-- Web Line -->
        <line x1="60" y1="0" x2="60" y2="45" stroke="#ffffff" stroke-width="2.5" filter="url(#webGlow)"/>

        <!-- Spider-Sense Tingle Arcs (Hidden by default, triggered on hover/threat) -->
        <g class="spidey-sense-waves" id="hangingSpideySense" opacity="0">
            <path d="M 40 145 Q 32 155 35 168" stroke="#ffeb3b" stroke-width="2.5" fill="none"/>
            <path d="M 32 142 Q 22 155 26 172" stroke="#ff1744" stroke-width="2.5" fill="none"/>
            <path d="M 80 145 Q 88 155 85 168" stroke="#ffeb3b" stroke-width="2.5" fill="none"/>
            <path d="M 88 142 Q 98 155 94 172" stroke="#ff1744" stroke-width="2.5" fill="none"/>
        </g>

        <!-- Upside-Down Body Group -->
        <g id="hangingBody">
            <!-- Feet holding web line -->
            <path d="M 52 42 Q 60 38 68 42 Q 65 48 60 48 Q 55 48 52 42 Z" fill="#b71c1c" stroke="#111" stroke-width="1.5"/>

            <!-- Legs (Upside-Down Bent Knees Pose) -->
            <!-- Left Leg (Blue/Red boot) -->
            <path d="M 46 65 L 54 44 L 59 44 L 54 68 Z" fill="#b71c1c" stroke="#111" stroke-width="1.5"/>
            <path d="M 45 66 L 38 90 L 48 94 L 54 68 Z" fill="#0d47a1" stroke="#111" stroke-width="1.5"/>
            <!-- Right Leg (Blue/Red boot) -->
            <path d="M 74 65 L 66 44 L 61 44 L 66 68 Z" fill="#b71c1c" stroke="#111" stroke-width="1.5"/>
            <path d="M 75 66 L 82 90 L 72 94 L 66 68 Z" fill="#0d47a1" stroke="#111" stroke-width="1.5"/>

            <!-- Torso (Upside-Down: Blue flanks, Red chest/belly with black webbing) -->
            <path d="M 42 88 L 78 88 L 72 125 L 48 125 Z" fill="#0d47a1" stroke="#111" stroke-width="1.5"/>
            <path d="M 50 88 L 70 88 L 66 125 L 54 125 Z" fill="#d32f2f" stroke="#111" stroke-width="1.5"/>

            <!-- Black Chest Webbing Tracery -->
            <path d="M 50 96 L 70 96 M 52 106 L 68 106 M 53 116 L 67 116" stroke="#111111" stroke-width="1"/>
            <line x1="60" y1="88" x2="60" y2="125" stroke="#111111" stroke-width="1"/>
            <line x1="60" y1="96" x2="52" y2="125" stroke="#111111" stroke-width="1"/>
            <line x1="60" y1="96" x2="68" y2="125" stroke="#111111" stroke-width="1"/>

            <!-- Black Spider Crest (Upside Down) -->
            <ellipse cx="60" cy="104" rx="3.5" ry="5.5" fill="#111111"/>
            <path d="M 57 100 Q 52 94 48 98 M 63 100 Q 68 94 72 98 M 57 104 Q 50 102 46 108 M 63 104 Q 70 102 74 108 M 58 107 Q 52 112 49 116 M 62 107 Q 68 112 71 116 M 59 109 Q 54 116 52 121 M 61 109 Q 66 116 68 121" stroke="#111111" stroke-width="1.2" fill="none"/>

            <!-- Arms crossed casually / holding web -->
            <!-- Left Arm -->
            <path d="M 42 92 Q 32 108 40 120 Q 48 118 45 106 Z" fill="#d32f2f" stroke="#111" stroke-width="1.5"/>
            <!-- Right Arm -->
            <path d="M 78 92 Q 88 108 80 120 Q 72 118 75 106 Z" fill="#d32f2f" stroke="#111" stroke-width="1.5"/>

            <!-- Upside-Down Head / Mask -->
            <path d="M 60 118 C 45 118 40 134 42 152 C 44 168 52 176 60 176 C 68 176 76 168 78 152 C 80 134 75 118 60 118 Z" fill="#d32f2f" stroke="#111" stroke-width="1.8"/>

            <!-- Head Web Tracery -->
            <line x1="60" y1="120" x2="60" y2="175" stroke="#111" stroke-width="1"/>
            <path d="M 44 140 Q 60 148 76 140 M 42 152 Q 60 162 78 152 M 46 164 Q 60 170 74 164" stroke="#111" stroke-width="1" fill="none"/>
            <line x1="60" y1="148" x2="45" y2="130" stroke="#111" stroke-width="0.8"/>
            <line x1="60" y1="148" x2="75" y2="130" stroke="#111" stroke-width="0.8"/>
            <line x1="60" y1="148" x2="43" y2="162" stroke="#111" stroke-width="0.8"/>
            <line x1="60" y1="148" x2="77" y2="162" stroke="#111" stroke-width="0.8"/>

            <!-- Iconic Large White Eye Lenses with Thick Black Border (Upside-Down Angle) -->
            <!-- Left Eye -->
            <path d="M 57 142 Q 46 140 47 154 Q 52 156 57 148 Z" fill="#111111"/>
            <path d="M 56 143 Q 48 142 49 152 Q 53 154 56 147 Z" fill="#ffffff" id="hangingLeftEye"/>
            <!-- Right Eye -->
            <path d="M 63 142 Q 74 140 73 154 Q 68 156 63 148 Z" fill="#111111"/>
            <path d="M 64 143 Q 72 142 71 152 Q 67 154 64 147 Z" fill="#ffffff" id="hangingRightEye"/>
        </g>
    </svg>
    `;

    /**
     * SVG for Corner Guardian Spider-Man Avatar
     * Heroic crouch avatar docked on the bottom-left monitor bezel (exactly like Spidey Tracker).
     */
    const GUARDIAN_SPIDEY_SVG = `
    <svg viewBox="0 0 100 120" class="guardian-spidey-svg" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="spideyRedGlow">
                <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#ff1744" flood-opacity="0.8"/>
            </filter>
        </defs>

        <!-- Spider-Sense Alert Sparks -->
        <g id="guardianSpideySense" opacity="0">
            <path d="M 28 20 Q 20 12 15 2" stroke="#ffeb3b" stroke-width="2.5" fill="none"/>
            <path d="M 22 25 Q 12 20 2 15" stroke="#ff1744" stroke-width="2.5" fill="none"/>
            <path d="M 72 20 Q 80 12 85 2" stroke="#ffeb3b" stroke-width="2.5" fill="none"/>
            <path d="M 78 25 Q 88 20 98 15" stroke="#ff1744" stroke-width="2.5" fill="none"/>
        </g>

        <!-- Spider-Man Crouch Silhouette -->
        <!-- Legs in Crouched Spider-Stance -->
        <path d="M 12 110 Q 18 85 35 92 L 32 114 Z" fill="#b71c1c" stroke="#111" stroke-width="1.8"/>
        <path d="M 88 110 Q 82 85 65 92 L 68 114 Z" fill="#b71c1c" stroke="#111" stroke-width="1.8"/>
        <path d="M 32 92 L 40 76 L 60 76 L 68 92 Z" fill="#0d47a1" stroke="#111" stroke-width="1.8"/>

        <!-- Torso & Arms -->
        <path d="M 30 52 L 70 52 L 62 82 L 38 82 Z" fill="#0d47a1" stroke="#111" stroke-width="1.8"/>
        <path d="M 40 52 L 60 52 L 56 82 L 44 82 Z" fill="#d32f2f" stroke="#111" stroke-width="1.8"/>

        <!-- Chest Webbing -->
        <line x1="50" y1="52" x2="50" y2="82" stroke="#111" stroke-width="1.2"/>
        <path d="M 42 60 L 58 60 M 43 70 L 57 70" stroke="#111" stroke-width="1"/>

        <!-- Black Chest Spider -->
        <ellipse cx="50" cy="65" rx="3" ry="5" fill="#111"/>
        <path d="M 47 62 Q 42 56 38 60 M 53 62 Q 58 56 62 60 M 47 67 Q 42 74 38 78 M 53 67 Q 58 74 62 78" stroke="#111" stroke-width="1.2" fill="none"/>

        <!-- Hands Perched Forward -->
        <path d="M 18 85 Q 24 72 32 64 L 28 85 Z" fill="#d32f2f" stroke="#111" stroke-width="1.5"/>
        <path d="M 82 85 Q 76 72 68 64 L 72 85 Z" fill="#d32f2f" stroke="#111" stroke-width="1.5"/>
        <!-- Hand Grips -->
        <ellipse cx="22" cy="88" rx="5" ry="4" fill="#b71c1c" stroke="#111" stroke-width="1.5"/>
        <ellipse cx="78" cy="88" rx="5" ry="4" fill="#b71c1c" stroke="#111" stroke-width="1.5"/>

        <!-- Iconic Spider-Man Mask Head -->
        <path d="M 50 14 C 32 14 26 30 28 48 C 30 62 40 70 50 70 C 60 70 70 62 72 48 C 74 30 68 14 50 14 Z" fill="#d32f2f" stroke="#111" stroke-width="2" filter="url(#spideyRedGlow)"/>

        <!-- Head Web Lines -->
        <line x1="50" y1="16" x2="50" y2="68" stroke="#111" stroke-width="1.2"/>
        <path d="M 32 32 Q 50 26 68 32 M 30 46 Q 50 38 70 46 M 34 58 Q 50 52 66 58" stroke="#111" stroke-width="1" fill="none"/>
        <line x1="50" y1="42" x2="30" y2="24" stroke="#111" stroke-width="0.8"/>
        <line x1="50" y1="42" x2="70" y2="24" stroke="#111" stroke-width="0.8"/>
        <line x1="50" y1="42" x2="28" y2="56" stroke="#111" stroke-width="0.8"/>
        <line x1="50" y1="42" x2="72" y2="56" stroke="#111" stroke-width="0.8"/>

        <!-- Large Signature White Spider Eyes with Bold Black Contour -->
        <path d="M 46 36 Q 30 35 32 52 Q 40 56 46 44 Z" fill="#111111"/>
        <path d="M 45 38 Q 33 37 34 50 Q 40 53 45 44 Z" fill="#ffffff" class="spidey-eye-lens" id="guardianLeftEye"/>

        <path d="M 54 36 Q 70 35 68 52 Q 60 56 54 44 Z" fill="#111111"/>
        <path d="M 55 38 Q 67 37 66 50 Q 60 53 55 44 Z" fill="#ffffff" class="spidey-eye-lens" id="guardianRightEye"/>
    </svg>
    `;

    /**
     * Initializes the interactive Spidey Tracker components
     */
    function initSpideyTrackerElements() {
        // 1. Mount Hanging Upside-Down Spider-Man
        mountHangingSpidey();

        // 2. Mount Guardian Spider-Man Avatar
        mountGuardianSpidey();

        // 3. Mount Radar Scanner
        mountRadarScanner();

        // 4. Bind interactive speech bubble & mouse tracking
        bindSpideyInteractivity();
    }

    function mountHangingSpidey() {
        if (document.getElementById('hangingSpideyContainer')) return;

        const container = document.createElement('div');
        container.id = 'hangingSpideyContainer';
        container.className = 'hanging-spidey-wrap';
        container.title = 'Click Spider-Man for forensic tip!';
        container.innerHTML = `
            ${HANGING_SPIDEY_SVG}
            <div class="spidey-speech-bubble" id="hangingSpideyBubble">
                <strong>"Hey! My Spider-Sense is tingling!</strong><br>
                Always check if the recruiter uses free Gmail instead of the company's real domain!"
            </div>
        `;

        document.body.appendChild(container);
    }

    function mountGuardianSpidey() {
        const bezelCorner = document.getElementById('spideyBezelAvatar');
        if (bezelCorner) {
            bezelCorner.innerHTML = GUARDIAN_SPIDEY_SVG;
        }
    }

    function mountRadarScanner() {
        const radarBox = document.getElementById('spideyRadarWidget');
        if (!radarBox) return;

        radarBox.innerHTML = `
            <div class="spidey-radar-circle">
                <div class="radar-sweep-beam"></div>
                <div class="radar-web-ring r1"></div>
                <div class="radar-web-ring r2"></div>
                <div class="radar-web-spoke s1"></div>
                <div class="radar-web-spoke s2"></div>
                <div class="radar-threat-blip b1" title="Threat: Advance Fee Fraud spotted"></div>
                <div class="radar-threat-blip b2" title="Threat: Fake Domain Detected"></div>
            </div>
            <div class="radar-status-caption">
                <span class="hud-indicator-dot red"></span>
                <span>SPIDEY RADAR: 2 THREATS INTERCEPTED</span>
            </div>
        `;
    }

    function bindSpideyInteractivity() {
        const hangingSpidey = document.getElementById('hangingSpideyContainer');
        const bubble = document.getElementById('hangingSpideyBubble');
        const senseWaves = document.getElementById('hangingSpideySense');

        const tips = [
            `"My Spider-Sense is tingling! Legitimate companies never demand ₹5,000 for training or equipment!"`,
            `"Watch out! If an offer sounds too good to be true ($75/hr for zero experience), it's a web of lies!"`,
            `"Recruiter talking only on Telegram? Classic impersonation trick. Don't send your Aadhaar or SSN!"`,
            `"Always independently verify the job opening on the employer's official careers portal!"`,
            `"Need backup? Click 'Ask CaseAI' to investigate every clue in your offer letter!"`
        ];

        let tipIndex = 0;

        if (hangingSpidey) {
            // Hover trigger
            hangingSpidey.addEventListener('mouseenter', () => {
                if (senseWaves) senseWaves.style.opacity = '1';
                if (window.SpiderAudio) window.SpiderAudio.playThreat();
            });

            hangingSpidey.addEventListener('mouseleave', () => {
                if (senseWaves) senseWaves.style.opacity = '0';
            });

            // Click trigger: change tip & play web shoot
            hangingSpidey.addEventListener('click', (e) => {
                e.stopPropagation();
                tipIndex = (tipIndex + 1) % tips.length;
                bubble.innerHTML = `<strong>Spidey Forensic Tip:</strong><br>${tips[tipIndex]}`;
                bubble.classList.add('visible');

                if (window.SpiderAudio) window.SpiderAudio.playWebShoot();

                // Animate pendulum sway
                hangingSpidey.classList.add('swaying');
                setTimeout(() => hangingSpidey.classList.remove('swaying'), 1200);

                setTimeout(() => {
                    bubble.classList.remove('visible');
                }, 5000);
            });
        }

        // Trigger Spider-Sense when hovering over any threat card on the page
        document.querySelectorAll('.threat-fragment-card, .network-node-bubble.threat').forEach(card => {
            card.addEventListener('mouseenter', () => {
                triggerSpiderSense();
            });
            card.addEventListener('mouseleave', () => {
                resetSpiderSense();
            });
        });
    }

    function triggerSpiderSense() {
        const sense1 = document.getElementById('hangingSpideySense');
        const sense2 = document.getElementById('guardianSpideySense');
        if (sense1) sense1.style.opacity = '1';
        if (sense2) sense2.style.opacity = '1';

        const hangingSpidey = document.getElementById('hangingSpideyContainer');
        if (hangingSpidey) hangingSpidey.classList.add('tingling');
    }

    function resetSpiderSense() {
        const sense1 = document.getElementById('hangingSpideySense');
        const sense2 = document.getElementById('guardianSpideySense');
        if (sense1) sense1.style.opacity = '0';
        if (sense2) sense2.style.opacity = '0';

        const hangingSpidey = document.getElementById('hangingSpideyContainer');
        if (hangingSpidey) hangingSpidey.classList.remove('tingling');
    }

    window.SpideyAssets = {
        init: initSpideyTrackerElements,
        triggerSpiderSense: triggerSpiderSense,
        resetSpiderSense: resetSpiderSense
    };

    document.addEventListener('DOMContentLoaded', initSpideyTrackerElements);
})();
