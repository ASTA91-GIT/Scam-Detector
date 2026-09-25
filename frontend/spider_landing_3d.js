/**
 * 3D Spider-Man-Inspired Cybersecurity Visual Engine
 * Built with Three.js (Procedural Futuristic City, 3D Cyber-Hero Silhouette,
 * Digital Spider-Web Network, Interactive Web-Shooter, and Mouse Parallax)
 */

(function () {
    let container, canvas;
    let scene, camera, renderer;
    let cityGroup, webGroup, heroGroup, particlesMesh;
    let webLines, heroHead, heroTorso, leftGauntlet, rightGauntlet;
    let cursorLight, redKeyLight, cyanRimLight;

    // Mouse & Animation State
    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    const windowHalf = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    let scrollProgress = 0;
    let activeWebShots = [];
    const clock = new THREE.Clock();

    const isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isMobile = window.innerWidth < 768;

    function init() {
        container = document.getElementById('spiderCanvasContainer');
        if (!container) return;

        // 1. Scene & Atmospheric Fog
        scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(0x060913, 0.013);

        // 2. Camera
        camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.5, 300);
        camera.position.set(0, 2, 28);

        // 3. Renderer
        renderer = new THREE.WebGLRenderer({ antialias: !isMobile, alpha: true, powerPreference: 'high-performance' });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2));
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.1;
        container.appendChild(renderer.domElement);
        canvas = renderer.domElement;

        // 4. Lighting System (Cinematic Spider-Red & Electric Cyan Rim)
        const ambientLight = new THREE.AmbientLight(0x0a1128, 0.8);
        scene.add(ambientLight);

        // Dynamic Cursor Light
        cursorLight = new THREE.PointLight(0x00e5ff, 2.5, 35);
        cursorLight.position.set(0, 4, 15);
        scene.add(cursorLight);

        // Spider-Red Key Light (Dramatic angle from left)
        redKeyLight = new THREE.DirectionalLight(0xff1744, 2.8);
        redKeyLight.position.set(-15, 12, 10);
        scene.add(redKeyLight);

        // Electric Cyan Rim Light (Sharp rim from right)
        cyanRimLight = new THREE.DirectionalLight(0x00e5ff, 2.2);
        cyanRimLight.position.set(18, -6, -5);
        scene.add(cyanRimLight);

        // 5. Build Procedural Elements
        buildProceduralCity();
        buildDigitalSpiderWeb();
        buildCyberHeroSilhouette();
        buildCyberDustParticles();

        // 6. Bind Event Listeners
        window.addEventListener('resize', onWindowResize);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('scroll', onScroll, { passive: true });

        // Web shooter click interaction on hero section
        const heroSection = document.querySelector('.spider-hero-viewport');
        if (heroSection) {
            heroSection.addEventListener('click', onHeroSectionClick);
        }

        // Start render loop
        animate();
    }

    /**
     * Procedural Nighttime Cyber City (Skyscrapers with glowing window patterns)
     */
    function buildProceduralCity() {
        cityGroup = new THREE.Group();

        // Window glow texture generator
        const windowCanvas = document.createElement('canvas');
        windowCanvas.width = 128;
        windowCanvas.height = 256;
        const ctx = windowCanvas.getContext('2d');
        ctx.fillStyle = '#080d1a';
        ctx.fillRect(0, 0, 128, 256);

        // Random window dots
        for (let y = 8; y < 250; y += 12) {
            for (let x = 6; x < 122; x += 10) {
                const rand = Math.random();
                if (rand > 0.6) {
                    ctx.fillStyle = rand > 0.92 ? '#00e5ff' : (rand > 0.82 ? '#ff1744' : '#ffd54f');
                    ctx.fillRect(x, y, 6, 8);
                }
            }
        }
        const windowTex = new THREE.CanvasTexture(windowCanvas);
        windowTex.wrapS = THREE.RepeatWrapping;
        windowTex.wrapT = THREE.RepeatWrapping;

        const buildingMat = new THREE.MeshStandardMaterial({
            color: 0x0c1424,
            roughness: 0.7,
            metalness: 0.4,
            map: windowTex
        });

        const numBuildings = isMobile ? 35 : 65;
        for (let i = 0; i < numBuildings; i++) {
            const h = 18 + Math.random() * 45;
            const w = 4 + Math.random() * 7;
            const d = 4 + Math.random() * 7;
            const geo = new THREE.BoxGeometry(w, h, d);
            const mesh = new THREE.Mesh(geo, buildingMat);

            const x = (Math.random() - 0.5) * 120;
            const z = -25 - Math.random() * 70;
            const y = h / 2 - 20;

            mesh.position.set(x, y, z);
            cityGroup.add(mesh);

            // Antenna beacon on tall buildings
            if (h > 35) {
                const beaconGeo = new THREE.CylinderGeometry(0.08, 0.08, 4, 4);
                const beaconMat = new THREE.MeshBasicMaterial({ color: Math.random() > 0.5 ? 0xff1744 : 0x00e5ff });
                const beacon = new THREE.Mesh(beaconGeo, beaconMat);
                beacon.position.set(x, y + h / 2 + 2, z);
                cityGroup.add(beacon);
            }
        }

        scene.add(cityGroup);
    }

    /**
     * 3D Digital Spider-Web Network Structure
     */
    function buildDigitalSpiderWeb() {
        webGroup = new THREE.Group();

        const numRays = 14;
        const numRings = 8;
        const radius = 22;

        const webVertices = [];
        const ringPoints = [];

        // Generate radial spokes
        for (let i = 0; i < numRays; i++) {
            const angle = (i / numRays) * Math.PI * 2;
            const cos = Math.cos(angle);
            const sin = Math.sin(angle);

            webVertices.push(0, 0, 0);
            webVertices.push(cos * radius, sin * radius, -2 + Math.sin(angle * 3) * 1.5);
        }

        // Generate polygon rings
        for (let r = 1; r <= numRings; r++) {
            const ringRadius = (r / numRings) * radius;
            const pts = [];
            for (let i = 0; i <= numRays; i++) {
                const angle = ((i % numRays) / numRays) * Math.PI * 2;
                const cos = Math.cos(angle);
                const sin = Math.sin(angle);
                const zOffset = Math.sin(r + angle * 2) * 0.8;
                pts.push(new THREE.Vector3(cos * ringRadius, sin * ringRadius, zOffset));
            }
            ringPoints.push(pts);
        }

        for (let r = 0; r < ringPoints.length; r++) {
            const pts = ringPoints[r];
            for (let i = 0; i < pts.length - 1; i++) {
                webVertices.push(pts[i].x, pts[i].y, pts[i].z);
                webVertices.push(pts[i + 1].x, pts[i + 1].y, pts[i + 1].z);
            }
        }

        const webGeo = new THREE.BufferGeometry();
        webGeo.setAttribute('position', new THREE.Float32BufferAttribute(webVertices, 3));

        const webMat = new THREE.LineBasicMaterial({
            color: 0x00e5ff,
            transparent: true,
            opacity: 0.35,
            blending: THREE.AdditiveBlending
        });

        webLines = new THREE.LineSegments(webGeo, webMat);
        webGroup.add(webLines);

        // Nodes on ring intersections
        const nodeGeo = new THREE.SphereGeometry(0.12, 6, 6);
        const nodeMat = new THREE.MeshBasicMaterial({ color: 0xff1744 });
        for (let i = 0; i < ringPoints.length; i += 2) {
            for (let j = 0; j < ringPoints[i].length; j += 2) {
                const node = new THREE.Mesh(nodeGeo, nodeMat);
                node.position.copy(ringPoints[i][j]);
                webGroup.add(node);
            }
        }

        webGroup.position.set(0, 1, -2);
        scene.add(webGroup);
    }

    /**
     * Iconic 3D Spider-Man Model & Perch
     * Recreates the classic red & blue suit, black webbing, large white eye lenses, and athletic crouch pose.
     */
    function buildCyberHeroSilhouette() {
        heroGroup = new THREE.Group();

        // Suit Color Palette
        const spideyRedMat = new THREE.MeshStandardMaterial({
            color: 0xd32f2f, // Iconic Spider Red
            roughness: 0.35,
            metalness: 0.25
        });
        const spideyBlueMat = new THREE.MeshStandardMaterial({
            color: 0x0d47a1, // Classic Suit Cobalt Blue
            roughness: 0.4,
            metalness: 0.3
        });
        const webLineMat = new THREE.LineBasicMaterial({
            color: 0x111111,
            linewidth: 2
        });
        const lensWhiteMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
        const lensBlackBorderMat = new THREE.MeshBasicMaterial({ color: 0x111111 });

        // 1. Skyscraper Perch Rooftop Ledge
        const ledgeGeo = new THREE.BoxGeometry(6, 1.4, 5);
        const ledgeMat = new THREE.MeshStandardMaterial({ color: 0x0a0f1d, roughness: 0.85 });
        const ledge = new THREE.Mesh(ledgeGeo, ledgeMat);
        ledge.position.set(0, -3.4, 0);
        heroGroup.add(ledge);

        // Neon cyber trim on ledge
        const ledgeEdgeGeo = new THREE.BoxGeometry(6.1, 0.12, 5.1);
        const ledgeEdgeMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });
        const ledgeEdge = new THREE.Mesh(ledgeEdgeGeo, ledgeEdgeMat);
        ledgeEdge.position.set(0, -2.7, 0);
        heroGroup.add(ledgeEdge);

        // 2. Head & Mask (Iconic Red Mask with Webbing & Signature Eyes)
        const headGeo = new THREE.SphereGeometry(0.9, 20, 16);
        headGeo.scale(0.85, 1.15, 0.95);
        heroHead = new THREE.Mesh(headGeo, spideyRedMat);
        heroHead.position.set(0, 1.6, 0.4);
        heroGroup.add(heroHead);

        // Mask Webbing Lines (Horizontal Latitudinal Rings)
        for (let r = -0.5; r <= 0.6; r += 0.25) {
            const ringGeo = new THREE.TorusGeometry(Math.cos(r) * 0.82, 0.015, 6, 24);
            const ring = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: 0x222222 }));
            ring.rotation.x = Math.PI / 2;
            ring.position.y = r * 1.1;
            heroHead.add(ring);
        }

        // Mask Vertical Web Lines
        for (let a = 0; a < 4; a++) {
            const lineGeo = new THREE.TorusGeometry(0.88, 0.015, 6, 24);
            const line = new THREE.Mesh(lineGeo, new THREE.MeshBasicMaterial({ color: 0x222222 }));
            line.rotation.y = (a * Math.PI) / 4;
            line.scale.set(0.85, 1.15, 0.95);
            heroHead.add(line);
        }

        // Signature Large Expressive Comic Eyes (Left & Right)
        function createSpideyEye(isLeft) {
            const eyeGroup = new THREE.Group();

            // Iconic Comic Spider Eye: sharp outer angle pointing up-out, curved lower edge
            const outerShape = new THREE.Shape();
            outerShape.moveTo(0, 0.44); // top outer tip
            outerShape.quadraticCurveTo(0.38, 0.12, 0.32, -0.36); // outer curved sweep
            outerShape.quadraticCurveTo(0.02, -0.26, -0.32, -0.16); // bottom edge
            outerShape.quadraticCurveTo(-0.28, 0.22, 0, 0.44); // inner slant
            const outerMesh = new THREE.Mesh(new THREE.ShapeGeometry(outerShape), lensBlackBorderMat);

            const innerShape = new THREE.Shape();
            innerShape.moveTo(0, 0.38);
            innerShape.quadraticCurveTo(0.32, 0.10, 0.27, -0.30);
            innerShape.quadraticCurveTo(0.02, -0.22, -0.26, -0.13);
            innerShape.quadraticCurveTo(-0.23, 0.19, 0, 0.38);
            const innerMesh = new THREE.Mesh(new THREE.ShapeGeometry(innerShape), lensWhiteMat);
            innerMesh.position.z = 0.02;

            eyeGroup.add(outerMesh);
            eyeGroup.add(innerMesh);

            const flip = isLeft ? 1 : -1;
            eyeGroup.scale.set(flip * 0.85, 0.85, 0.85);
            eyeGroup.rotation.y = isLeft ? -0.38 : 0.38;
            eyeGroup.rotation.z = isLeft ? -0.12 : 0.12;
            eyeGroup.position.set(isLeft ? -0.38 : 0.38, 0.05, 0.84);
            return eyeGroup;
        }

        heroHead.add(createSpideyEye(true));
        heroHead.add(createSpideyEye(false));

        // 3. Torso (Center Red with Black Spider Logo, Blue Flanks)
        const torsoGroup = new THREE.Group();
        torsoGroup.position.set(0, -0.3, 0.2);

        // Center Red Chest (V-Taper)
        const chestGeo = new THREE.CylinderGeometry(1.15, 0.75, 2.0, 10);
        heroTorso = new THREE.Mesh(chestGeo, spideyRedMat);
        torsoGroup.add(heroTorso);

        // Blue Side Panels (Flanks)
        const flankLeft = new THREE.Mesh(new THREE.BoxGeometry(0.35, 1.8, 0.85), spideyBlueMat);
        flankLeft.position.set(-0.95, 0, 0);
        torsoGroup.add(flankLeft);

        const flankRight = new THREE.Mesh(new THREE.BoxGeometry(0.35, 1.8, 0.85), spideyBlueMat);
        flankRight.position.set(0.95, 0, 0);
        torsoGroup.add(flankRight);

        // Iconic Black Spider Chest Emblem
        const spiderBodyGeo = new THREE.SphereGeometry(0.18, 8, 8);
        spiderBodyGeo.scale(0.7, 1.3, 0.3);
        const spiderBody = new THREE.Mesh(spiderBodyGeo, lensBlackBorderMat);
        spiderBody.position.set(0, 0.2, 0.98);
        torsoGroup.add(spiderBody);

        // Spider Legs spreading across chest
        for (let i = 0; i < 4; i++) {
            const side = i < 2 ? -1 : 1;
            const legGeo = new THREE.TorusGeometry(0.35 + (i % 2) * 0.15, 0.025, 4, 12, Math.PI / 1.8);
            const leg = new THREE.Mesh(legGeo, lensBlackBorderMat);
            leg.position.set(side * 0.3, 0.2 + (i % 2) * 0.2, 0.95);
            leg.rotation.z = side * (0.4 + (i % 2) * 0.6);
            torsoGroup.add(leg);
        }

        heroGroup.add(torsoGroup);

        // 4. Arms in Dynamic Spider Crouch Stance
        // Left Arm (Shoulder red, bicep blue, forearm/gauntlet red)
        const leftArmGroup = new THREE.Group();
        leftArmGroup.position.set(-1.15, 0.5, 0.2);

        const leftShoulder = new THREE.Mesh(new THREE.SphereGeometry(0.38, 8, 8), spideyRedMat);
        leftArmGroup.add(leftShoulder);

        const leftBicep = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.24, 1.3, 8), spideyBlueMat);
        leftBicep.position.set(-0.45, -0.55, 0.1);
        leftBicep.rotation.z = 0.5;
        leftArmGroup.add(leftBicep);

        leftGauntlet = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.22, 1.3, 8), spideyRedMat);
        leftGauntlet.position.set(-0.95, -1.45, 0.5);
        leftGauntlet.rotation.x = -0.5;
        leftArmGroup.add(leftGauntlet);

        // Left Hand Gripping Ledge
        const leftHand = new THREE.Mesh(new THREE.SphereGeometry(0.26, 6, 6), spideyRedMat);
        leftHand.position.set(-1.1, -2.1, 0.9);
        leftArmGroup.add(leftHand);

        heroGroup.add(leftArmGroup);

        // Right Arm (Forward Target Stance with Web Shooter Wrist)
        const rightArmGroup = new THREE.Group();
        rightArmGroup.position.set(1.15, 0.5, 0.2);

        const rightShoulder = new THREE.Mesh(new THREE.SphereGeometry(0.38, 8, 8), spideyRedMat);
        rightArmGroup.add(rightShoulder);

        const rightBicep = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.24, 1.3, 8), spideyBlueMat);
        rightBicep.position.set(0.45, -0.55, 0.1);
        rightBicep.rotation.z = -0.5;
        rightArmGroup.add(rightBicep);

        rightGauntlet = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.22, 1.3, 8), spideyRedMat);
        rightGauntlet.position.set(0.95, -1.45, 0.5);
        rightGauntlet.rotation.x = -0.5;
        rightArmGroup.add(rightGauntlet);

        // Right Web-Shooter Wrist Nozzle
        const webShooterNozzle = new THREE.Mesh(
            new THREE.CylinderGeometry(0.08, 0.08, 0.2, 8),
            new THREE.MeshBasicMaterial({ color: 0x00e5ff })
        );
        webShooterNozzle.position.set(1.15, -1.9, 0.9);
        webShooterNozzle.rotation.x = Math.PI / 2;
        rightArmGroup.add(webShooterNozzle);

        const rightHand = new THREE.Mesh(new THREE.SphereGeometry(0.26, 6, 6), spideyRedMat);
        rightHand.position.set(1.1, -2.1, 0.9);
        rightArmGroup.add(rightHand);

        heroGroup.add(rightArmGroup);



        // 5. Perched Crouch Legs (Blue Thighs, Red Spider Boots on Ledge)
        // Left Leg
        const leftThigh = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.32, 1.6, 8), spideyBlueMat);
        leftThigh.position.set(-1.0, -1.4, -0.2);
        leftThigh.rotation.x = 1.1;
        leftThigh.rotation.z = -0.4;
        heroGroup.add(leftThigh);

        const leftBoot = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.28, 1.8, 8), spideyRedMat);
        leftBoot.position.set(-1.3, -2.3, 0.5);
        leftBoot.rotation.x = -0.8;
        heroGroup.add(leftBoot);

        // Right Leg
        const rightThigh = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.32, 1.6, 8), spideyBlueMat);
        rightThigh.position.set(1.0, -1.4, -0.2);
        rightThigh.rotation.x = 1.1;
        rightThigh.rotation.z = 0.4;
        heroGroup.add(rightThigh);

        const rightBoot = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.28, 1.8, 8), spideyRedMat);
        rightBoot.position.set(1.3, -2.3, 0.5);
        rightBoot.rotation.x = -0.8;
        heroGroup.add(rightBoot);

        // Position hero towards right side of hero viewport (desktop) or center (mobile)
        heroGroup.position.set(isMobile ? 0 : 5.8, -0.4, 7.8);
        heroGroup.scale.set(1.15, 1.15, 1.15);
        scene.add(heroGroup);
    }

    /**
     * Floating Cybersecurity Particle Mesh
     */
    function buildCyberDustParticles() {
        const count = isMobile ? 120 : 350;
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);

        const colorCyan = new THREE.Color(0x00e5ff);
        const colorRed = new THREE.Color(0xff1744);

        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 50;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 35;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 40;

            const c = Math.random() > 0.3 ? colorCyan : colorRed;
            colors[i * 3] = c.r;
            colors[i * 3 + 1] = c.g;
            colors[i * 3 + 2] = c.b;
        }

        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const mat = new THREE.PointsMaterial({
            size: isMobile ? 0.25 : 0.35,
            vertexColors: true,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending
        });

        particlesMesh = new THREE.Points(geo, mat);
        scene.add(particlesMesh);
    }

    /**
     * Interactive Web-Shooter: Fires a 3D web-line from the hero toward click target
     */
    function onHeroSectionClick(e) {
        // Prevent trigger if clicking on interactive CTA buttons or links
        if (e.target.closest('a, button, input, textarea')) return;

        // Sound effect
        if (window.SpiderAudio) {
            window.SpiderAudio.playWebShoot();
        }

        // Raycast from 2D click into 3D world plane
        const rect = renderer.domElement.getBoundingClientRect();
        const mouseNormX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        const mouseNormY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(new THREE.Vector2(mouseNormX, mouseNormY), camera);

        const planeZ = new THREE.Plane(new THREE.Vector3(0, 0, 1), -4);
        const targetPoint = new THREE.Vector3();
        raycaster.ray.intersectPlane(planeZ, targetPoint);

        // Origin at right gauntlet
        const origin = new THREE.Vector3();
        if (rightGauntlet) {
            rightGauntlet.getWorldPosition(origin);
        } else {
            origin.set(5.5, -1.5, 8);
        }

        createWebShot(origin, targetPoint);
    }

    function createWebShot(origin, destination) {
        // 1. Web Line
        const lineGeo = new THREE.BufferGeometry().setFromPoints([origin, destination]);
        const lineMat = new THREE.LineBasicMaterial({
            color: 0x00e5ff,
            transparent: true,
            opacity: 1.0,
            blending: THREE.AdditiveBlending
        });
        const webLine = new THREE.Line(lineGeo, lineMat);
        scene.add(webLine);

        // 2. Web Impact Splash (Mini web burst on target)
        const splashCount = 12;
        const splashPoints = [];
        for (let i = 0; i < splashCount; i++) {
            const angle = (i / splashCount) * Math.PI * 2;
            const dist = 0.8 + Math.random() * 0.7;
            splashPoints.push(destination);
            splashPoints.push(new THREE.Vector3(
                destination.x + Math.cos(angle) * dist,
                destination.y + Math.sin(angle) * dist,
                destination.z + (Math.random() - 0.5) * 0.3
            ));
        }
        const splashGeo = new THREE.BufferGeometry().setFromPoints(splashPoints);
        const splashMat = new THREE.LineBasicMaterial({
            color: 0xff1744,
            transparent: true,
            opacity: 0.9,
            blending: THREE.AdditiveBlending
        });
        const splashLines = new THREE.LineSegments(splashGeo, splashMat);
        scene.add(splashLines);

        // Add to active shots for decay
        activeWebShots.push({
            line: webLine,
            splash: splashLines,
            life: 1.0,
            decay: 0.035
        });
    }

    function onMouseMove(e) {
        mouse.targetX = (e.clientX - windowHalf.x) / windowHalf.x;
        mouse.targetY = (e.clientY - windowHalf.y) / windowHalf.y;
    }

    function onScroll() {
        const docH = document.documentElement.scrollHeight - window.innerHeight;
        scrollProgress = docH > 0 ? window.scrollY / docH : 0;
    }

    function onWindowResize() {
        windowHalf.x = window.innerWidth / 2;
        windowHalf.y = window.innerHeight / 2;
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }

    /**
     * Animation & Render Loop
     */
    function animate() {
        requestAnimationFrame(animate);

        const delta = clock.getDelta();
        const time = clock.getElapsedTime();

        // 1. Smooth mouse lerp
        const lerpFactor = isReducedMotion ? 0.01 : 0.05;
        mouse.x += (mouse.targetX - mouse.x) * lerpFactor;
        mouse.y += (mouse.targetY - mouse.y) * lerpFactor;

        // 2. Point Light tracks cursor
        if (cursorLight) {
            cursorLight.position.x = mouse.x * 12;
            cursorLight.position.y = -mouse.y * 8 + 3;
        }

        // 3. Spider-Web Motion & Oscillation
        if (webGroup) {
            webGroup.rotation.z = Math.sin(time * 0.2) * 0.05;
            webGroup.rotation.x = -mouse.y * 0.15;
            webGroup.rotation.y = mouse.x * 0.18;
        }

        // 4. City subtle background parallax
        if (cityGroup) {
            cityGroup.position.x = -mouse.x * 2.5;
            cityGroup.position.y = mouse.y * 1.5;
        }

        // 5. Cyber Hero subtle look-at mouse tracking
        if (heroHead) {
            heroHead.rotation.y = mouse.x * 0.45;
            heroHead.rotation.x = -mouse.y * 0.3;
        }
        if (heroTorso) {
            heroTorso.rotation.y = mouse.x * 0.15;
        }

        // 6. Particles gentle drift
        if (particlesMesh) {
            particlesMesh.rotation.y = time * 0.02 + mouse.x * 0.05;
            particlesMesh.rotation.x = Math.sin(time * 0.03) * 0.05 - mouse.y * 0.05;
        }

        // 7. Scroll-based Camera Journey
        // 0% -> Hero view, 35% -> Threat zoom, 65% -> Network view, 100% -> Skyline CTA
        if (!isReducedMotion) {
            const targetCamZ = 28 - scrollProgress * 14;
            const targetCamY = 2 - scrollProgress * 8;
            camera.position.z += (targetCamZ - camera.position.z) * 0.06;
            camera.position.y += (targetCamY - camera.position.y) * 0.06;
            camera.rotation.x = -scrollProgress * 0.15;
        }

        // 8. Update Web Shot Lifespans
        for (let i = activeWebShots.length - 1; i >= 0; i--) {
            const shot = activeWebShots[i];
            shot.life -= shot.decay;
            shot.line.material.opacity = Math.max(0, shot.life);
            shot.splash.material.opacity = Math.max(0, shot.life);

            if (shot.life <= 0) {
                scene.remove(shot.line);
                scene.remove(shot.splash);
                shot.line.geometry.dispose();
                shot.line.material.dispose();
                shot.splash.geometry.dispose();
                shot.splash.material.dispose();
                activeWebShots.splice(i, 1);
            }
        }

        renderer.render(scene, camera);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
