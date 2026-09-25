/**
 * Cyber Web Audio Synthesizer
 * Uses native Web Audio API to generate high-tech cybernetic sound effects
 * without any external audio asset dependencies.
 * Default state: OFF.
 */

(function() {
    let audioCtx = null;
    let isSoundEnabled = false;

    function initAudio() {
        if (!audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            audioCtx = new AudioContext();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
    }

    /**
     * Web-Shooter "Thwip" Cyber Acoustic Burst
     */
    function playWebShootSound() {
        if (!isSoundEnabled || !audioCtx) return;
        try {
            const now = audioCtx.currentTime;

            // 1. High frequency web-strand tension sweep
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(1400, now);
            osc.frequency.exponentialRampToValueAtTime(180, now + 0.18);

            gain.gain.setValueAtTime(0.25, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);

            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start(now);
            osc.stop(now + 0.18);

            // 2. Filtered noise burst for web ejection
            const bufferSize = audioCtx.sampleRate * 0.12;
            const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
            const data = buffer.getChannelData(0);
            for (let i = 0; i < bufferSize; i++) {
                data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.3));
            }

            const noise = audioCtx.createBufferSource();
            noise.buffer = buffer;

            const filter = audioCtx.createBiquadFilter();
            filter.type = 'bandpass';
            filter.frequency.setValueAtTime(3200, now);
            filter.frequency.exponentialRampToValueAtTime(600, now + 0.12);
            filter.Q.value = 3.0;

            const noiseGain = audioCtx.createGain();
            noiseGain.gain.setValueAtTime(0.18, now);
            noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);

            noise.connect(filter);
            filter.connect(noiseGain);
            noiseGain.connect(audioCtx.destination);

            noise.start(now);
            noise.stop(now + 0.12);
        } catch (e) {
            console.warn('Audio play error:', e);
        }
    }

    /**
     * Cyber HUD Hover Beep
     */
    function playHoverSound() {
        if (!isSoundEnabled || !audioCtx) return;
        try {
            const now = audioCtx.currentTime;
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.exponentialRampToValueAtTime(1760, now + 0.04);

            gain.gain.setValueAtTime(0.04, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start(now);
            osc.stop(now + 0.04);
        } catch (e) {}
    }

    /**
     * Threat Node Alert Sound
     */
    function playThreatSound() {
        if (!isSoundEnabled || !audioCtx) return;
        try {
            const now = audioCtx.currentTime;
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(320, now);
            osc.frequency.setValueAtTime(440, now + 0.08);

            gain.gain.setValueAtTime(0.08, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start(now);
            osc.stop(now + 0.22);
        } catch (e) {}
    }

    function toggleSound() {
        initAudio();
        isSoundEnabled = !isSoundEnabled;
        localStorage.setItem('spider_sound_enabled', isSoundEnabled ? 'true' : 'false');
        updateSoundButtons();
        if (isSoundEnabled) {
            playHoverSound();
        }
        return isSoundEnabled;
    }

    function updateSoundButtons() {
        const btns = document.querySelectorAll('.spider-sound-toggle');
        btns.forEach(btn => {
            if (isSoundEnabled) {
                btn.innerHTML = `<span style="color:#00e5ff;">🔊 Sound: ON</span>`;
                btn.setAttribute('aria-pressed', 'true');
            } else {
                btn.innerHTML = `<span style="color:var(--text-muted);">🔇 Sound: OFF</span>`;
                btn.setAttribute('aria-pressed', 'false');
            }
        });
    }

    // Initialize state
    document.addEventListener('DOMContentLoaded', () => {
        isSoundEnabled = localStorage.getItem('spider_sound_enabled') === 'true';
        updateSoundButtons();

        document.querySelectorAll('.spider-sound-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                toggleSound();
            });
        });
    });

    window.SpiderAudio = {
        playWebShoot: playWebShootSound,
        playHover: playHoverSound,
        playThreat: playThreatSound,
        toggleSound: toggleSound,
        isEnabled: () => isSoundEnabled
    };
})();
