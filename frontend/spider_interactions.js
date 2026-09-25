/**
 * Spider-Man Cybersecurity Interactive Controller
 * Custom Cyber-Reticle Cursor, Interactive CaseAI Chat Simulation,
 * Holographic Node Inspection, Sound Integration, and Scroll Navbar
 */

(function () {
    document.addEventListener('DOMContentLoaded', () => {
        setupCustomCursor();
        setupNavbarScroll();
        setupCaseAiSimulation();
        setupInteractiveNetwork();
        setupSoundEffects();
    });

    /**
     * 1. Custom Cyber-Reticle Cursor (Smooth Lerp + Dynamic Web Crosshair Expansion)
     */
    function setupCustomCursor() {
        if (window.matchMedia('(hover: none), (pointer: coarse)').matches) return;

        const dot = document.createElement('div');
        dot.className = 'spider-cursor-dot';
        const reticle = document.createElement('div');
        reticle.className = 'spider-cursor-reticle';

        document.body.appendChild(dot);
        document.body.appendChild(reticle);

        let mouseX = -100, mouseY = -100;
        let reticleX = -100, reticleY = -100;

        window.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;
            dot.style.left = `${mouseX}px`;
            dot.style.top = `${mouseY}px`;
        });

        function renderCursor() {
            reticleX += (mouseX - reticleX) * 0.18;
            reticleY += (mouseY - reticleY) * 0.18;
            reticle.style.left = `${reticleX}px`;
            reticle.style.top = `${reticleY}px`;
            requestAnimationFrame(renderCursor);
        }
        renderCursor();

        // Expand on hover
        const interactiveElements = 'a, button, input, textarea, .threat-fragment-card, .network-node-bubble, .spider-feature-card';
        document.querySelectorAll(interactiveElements).forEach(el => {
            el.addEventListener('mouseenter', () => {
                document.body.classList.add('spider-cursor-hover');
                if (window.SpiderAudio) window.SpiderAudio.playHover();
            });
            el.addEventListener('mouseleave', () => {
                document.body.classList.remove('spider-cursor-hover');
            });
        });
    }

    /**
     * 2. Navbar Scroll Solidification
     */
    function setupNavbarScroll() {
        const navbar = document.querySelector('.spider-navbar');
        if (!navbar) return;

        window.addEventListener('scroll', () => {
            if (window.scrollY > 40) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }, { passive: true });
    }

    /**
     * 3. Section 5: Animated CaseAI Chat Simulator
     */
    function setupCaseAiSimulation() {
        const chatWindow = document.getElementById('spiderCaseAiDemoMessages');
        if (!chatWindow) return;

        const demoExchanges = [
            {
                q: "Why was this software developer offer flagged as High Risk?",
                a: "Based on forensic evidence in this case:\n1. [EVIDENCE] The recruiter is using a generic webmail address (@gmail.com) rather than the corporate domain.\n2. [EVIDENCE] Section 4 demands a ₹5,000 security deposit for laptop dispatch.\n3. [INFERENCE] Legitimate enterprise employers never require candidate payment for hardware.\n\n[RECOMMENDATION] Halt communication and verify directly on the company's official careers portal."
            },
            {
                q: "Does the recruiter's email domain match the company website?",
                a: "Verification Signal: DOMAIN MISMATCH.\nThe official company website is registered to apextechnologies.com, but recruitment correspondence originated from apex-jobs-hr@gmail.com. This strongly suggests impersonation."
            },
            {
                q: "Generate a strategic question to test this recruiter.",
                a: "Ask: \"Can you provide the official Job Requisition ID and confirm who the primary corporate signatory is on your enterprise email domain?\" Genuine recruiters will readily furnish official requisition credentials."
            }
        ];

        let index = 0;

        function playExchange() {
            const exchange = demoExchanges[index % demoExchanges.length];
            chatWindow.innerHTML = `
                <div class="caseai-message-row user" style="margin-bottom:0.75rem;">
                    <div class="caseai-message-avatar">👤</div>
                    <div class="caseai-message-bubble" style="background:linear-gradient(135deg, rgba(255,23,68,0.25), rgba(0,229,255,0.25)); border-color:var(--spider-cyan); color:#ffffff;">
                        ${exchange.q}
                    </div>
                </div>
                <div class="caseai-message-row assistant">
                    <div class="caseai-message-avatar" style="color:var(--spider-cyan);">✦</div>
                    <div class="caseai-message-bubble" style="white-space:pre-line;" id="simulatedAiResponse">
                        <span class="caseai-typing-cursor"></span>
                    </div>
                </div>
            `;

            const respEl = document.getElementById('simulatedAiResponse');
            let charPos = 0;
            const text = exchange.a;

            function typeChar() {
                if (charPos < text.length) {
                    charPos += 3;
                    respEl.innerHTML = text.substring(0, charPos) + `<span class="caseai-typing-cursor"></span>`;
                    setTimeout(typeChar, 20);
                } else {
                    respEl.innerHTML = text;
                    index++;
                    setTimeout(playExchange, 6000);
                }
            }
            setTimeout(typeChar, 400);
        }

        // Start cycle
        setTimeout(playExchange, 1500);
    }

    /**
     * 4. Section 7: Interactive Investigation Network Nodes
     */
    function setupInteractiveNetwork() {
        const tooltip = document.getElementById('networkTooltipBox');
        if (!tooltip) return;

        const nodeData = {
            company: {
                title: "🏢 Identified Employer Entity",
                desc: "Official corporate registry and business name verification cross-referenced against established public filings."
            },
            website: {
                title: "🌐 Corporate Domain & DNS",
                desc: "WHOIS age, SSL certificate authority, and MX DNS record resolution to verify domain authenticity."
            },
            recruiter: {
                title: "👤 Recruiter Digital Footprint",
                desc: "Tenure analysis, verified talent acquisition role, and corporate communications authority."
            },
            email: {
                title: "✉️ Domain Matching Vector",
                desc: "Checks whether email headers and recruiter addresses originate from authentic enterprise mail servers or free webmail."
            },
            job: {
                title: "📄 Compensation & Requirement Integrity",
                desc: "Evaluates unrealistic compensation promises, vague job descriptions, and suspicious interview bypasses."
            },
            signal: {
                title: "🚨 Advance Fee / Urgency Threat Signal",
                desc: "Forensic heuristic detection of cryptocurrency requests, gift cards, equipment deposits, or time-coercion tactics."
            }
        };

        document.querySelectorAll('.network-node-bubble').forEach(node => {
            node.addEventListener('mouseenter', (e) => {
                const type = node.getAttribute('data-node');
                const info = nodeData[type];
                if (info) {
                    tooltip.innerHTML = `
                        <h4 style="color:var(--spider-cyan); margin-bottom:0.25rem; font-size:1rem;">${info.title}</h4>
                        <p style="color:#94a3b8; font-size:0.86rem; margin:0;">${info.desc}</p>
                    `;
                    tooltip.style.borderColor = type === 'signal' ? 'var(--spider-red)' : 'var(--spider-cyan)';
                }
                if (window.SpiderAudio && type === 'signal') {
                    window.SpiderAudio.playThreat();
                }
            });
        });
    }

    /**
     * 5. Audio click triggers
     */
    function setupSoundEffects() {
        document.querySelectorAll('.threat-fragment-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                if (window.SpiderAudio) window.SpiderAudio.playThreat();
            });
        });
    }
})();
