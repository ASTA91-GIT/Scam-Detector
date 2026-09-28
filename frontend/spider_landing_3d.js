/**
 * Cinematic 3D Spider-Man Hero & Nighttime NYC Rooftop Scene
 * Inspired by modern Spider-Man film cinematography:
 * - Nighttime New York rooftop atmosphere
 * - Cool moonlight key light & dramatic Red/Blue rim lights
 * - Large 3D Spider-Man hero in an athletic crouch pose (supports external GLTF + sculpted cinematic fallback)
 * - Single subtle web element behind hero
 * - Authentic distant skyline with misty atmospheric fog
 * - Drag-to-rotate interaction, subtle idle breathing, and smooth mouse parallax
 */

(function () {
    let container, canvas;
    let scene, camera, renderer;
    let cityGroup, webGroup, heroGroup, rooftopGroup, dustParticles;
    let heroHead, heroChest, leftArmPivot, rightArmPivot;
    let moonLight, redRimLight, blueRimLight, cursorLight;

    // Mouse, Drag & State
    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    const windowHalf = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    let isDragging = false;
    let dragStartX = 0;
    let heroRotationY = -0.32;
    let targetHeroRotationY = -0.32;
    let hasInteractedWithRotation = false;

    let scrollProgress = 0;
    const clock = new THREE.Clock();

    const isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let isMobile = window.innerWidth < 992;

    function init() {
        container = document.getElementById('spiderCanvasContainer');
        if (!container) return;

        // 1. Scene & Cinematic Fog
        scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(0x05070d, 0.015);

        // 2. Camera: Cinematic Low-Angle Perspective
        camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.5, 320);
        updateCameraPosition();

        // 3. WebGL Renderer
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2));
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.08;
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        container.appendChild(renderer.domElement);
        canvas = renderer.domElement;

        // 4. Movie-Style Lighting System
        setupCinematicLighting();

        // 5. Build Environment Elements
        buildSkylineBackground();
        buildMoonGlow();
        buildRooftopAndMist();
        buildSingleSubtleSpiderWeb();
        buildAtmosphericDust();

        // 6. Build or Load 3D Spider-Man Hero
        buildHeroSystem();

        // 7. Event Handlers
        setupInteractionListeners();

        // Start render loop
        animate();
    }

    function updateCameraPosition() {
        isMobile = window.innerWidth < 992;
        if (isMobile) {
            camera.position.set(0, 2.2, 23);
            camera.lookAt(0, 1.2, 0);
        } else {
            camera.position.set(0, 1.8, 20);
            camera.lookAt(1.8, 1.5, 0);
        }
    }

    /**
     * Movie-Style Lighting Setup:
     * - Cool moonlight key light from above-behind
     * - Spider-Red rim light sculpting silhouette
     * - Cyan-Blue secondary rim light
     * - Rich deep ambient light
     */
    function setupCinematicLighting() {
        // Deep ambient tone for dark shadows (preserves mystery)
        const ambientLight = new THREE.AmbientLight(0x0a1122, 0.95);
        scene.add(ambientLight);

        // Cool Moonlight from high behind/above
        moonLight = new THREE.DirectionalLight(0xcde1f5, 1.85);
        moonLight.position.set(12, 22, -14);
        moonLight.castShadow = true;
        moonLight.shadow.mapSize.width = 1024;
        moonLight.shadow.mapSize.height = 1024;
        moonLight.shadow.camera.near = 0.5;
        moonLight.shadow.camera.far = 60;
        moonLight.shadow.camera.left = -10;
        moonLight.shadow.camera.right = 10;
        moonLight.shadow.camera.top = 10;
        moonLight.shadow.camera.bottom = -10;
        moonLight.shadow.bias = -0.001;
        scene.add(moonLight);

        // Spider-Red Rim Light (Carves the hero silhouette from the left/back)
        redRimLight = new THREE.DirectionalLight(0xe5092f, 2.7);
        redRimLight.position.set(-16, 8, -6);
        scene.add(redRimLight);

        // Electric Cyan-Blue Secondary Rim Light (Cuts across right flank)
        blueRimLight = new THREE.DirectionalLight(0x00b8ff, 1.6);
        blueRimLight.position.set(16, -2, 5);
        scene.add(blueRimLight);

        // Subtle soft cursor point light
        cursorLight = new THREE.PointLight(0x80d8ff, 0.65, 26);
        cursorLight.position.set(2, 3, 12);
        scene.add(cursorLight);
    }

    /**
     * Authentic Distant NYC Skyline Silhouettes
     * Varied building heights, architectural setbacks, spires, and sparse warm windows
     */
    function buildSkylineBackground() {
        cityGroup = new THREE.Group();

        // Sparse window texture generator (amber & moonlight dots at 3 AM)
        const winCanvas = document.createElement('canvas');
        winCanvas.width = 128;
        winCanvas.height = 256;
        const ctx = winCanvas.getContext('2d');
        ctx.fillStyle = '#060a14';
        ctx.fillRect(0, 0, 128, 256);

        for (let y = 6; y < 250; y += 14) {
            for (let x = 6; x < 122; x += 11) {
                const rand = Math.random();
                if (rand > 0.84) {
                    ctx.fillStyle = rand > 0.94 ? 'rgba(255, 214, 150, 0.85)' : 'rgba(147, 197, 253, 0.7)';
                    ctx.fillRect(x, y, 4, 6);
                }
            }
        }
        const winTex = new THREE.CanvasTexture(winCanvas);
        winTex.wrapS = THREE.RepeatWrapping;
        winTex.wrapT = THREE.RepeatWrapping;

        const buildingMaterial = new THREE.MeshStandardMaterial({
            color: 0x080e1b,
            roughness: 0.9,
            metalness: 0.2,
            map: winTex
        });

        const distantMaterial = new THREE.MeshBasicMaterial({
            color: 0x050913
        });

        // 1. Distant silhouette layer
        const numDistant = isMobile ? 20 : 42;
        for (let i = 0; i < numDistant; i++) {
            const h = 25 + Math.random() * 55;
            const w = 6 + Math.random() * 9;
            const d = 5 + Math.random() * 8;
            const bGeo = new THREE.BoxGeometry(w, h, d);
            const bMesh = new THREE.Mesh(bGeo, distantMaterial);

            const x = (Math.random() - 0.5) * 160;
            const z = -65 - Math.random() * 50;
            const y = h / 2 - 24;

            bMesh.position.set(x, y, z);
            cityGroup.add(bMesh);

            // Spire on tall buildings
            if (h > 55) {
                const spireGeo = new THREE.ConeGeometry(0.5, 9, 5);
                const spireMesh = new THREE.Mesh(spireGeo, distantMaterial);
                spireMesh.position.set(x, y + h / 2 + 4.5, z);
                cityGroup.add(spireMesh);
            }
        }

        // 2. Midground buildings with window lights
        const numMid = isMobile ? 18 : 36;
        for (let i = 0; i < numMid; i++) {
            const h = 20 + Math.random() * 40;
            const w = 5 + Math.random() * 8;
            const d = 5 + Math.random() * 8;
            const bGeo = new THREE.BoxGeometry(w, h, d);
            const bMesh = new THREE.Mesh(bGeo, buildingMaterial);

            const x = (Math.random() - 0.5) * 110;
            const z = -32 - Math.random() * 32;
            const y = h / 2 - 20;

            bMesh.position.set(x, y, z);
            cityGroup.add(bMesh);

            // Tiny red warning beacon on tall towers
            if (h > 42) {
                const beaconGeo = new THREE.SphereGeometry(0.18, 6, 6);
                const beaconMat = new THREE.MeshBasicMaterial({ color: 0xe5092f });
                const beacon = new THREE.Mesh(beaconGeo, beaconMat);
                beacon.position.set(x, y + h / 2 + 1.2, z);
                cityGroup.add(beacon);
            }
        }

        scene.add(cityGroup);
    }

    /**
     * Soft Lunar Glow in the Night Sky
     */
    function buildMoonGlow() {
        const moonCanvas = document.createElement('canvas');
        moonCanvas.width = 256;
        moonCanvas.height = 256;
        const ctx = moonCanvas.getContext('2d');
        const grad = ctx.createRadialGradient(128, 128, 20, 128, 128, 120);
        grad.addColorStop(0, 'rgba(235, 245, 255, 0.95)');
        grad.addColorStop(0.3, 'rgba(190, 220, 255, 0.35)');
        grad.addColorStop(0.7, 'rgba(100, 160, 230, 0.08)');
        grad.addColorStop(1, 'rgba(5, 7, 13, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 256, 256);

        const moonTexture = new THREE.CanvasTexture(moonCanvas);
        const moonGeo = new THREE.PlaneGeometry(36, 36);
        const moonMat = new THREE.MeshBasicMaterial({
            map: moonTexture,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        const moonMesh = new THREE.Mesh(moonGeo, moonMat);
        moonMesh.position.set(-18, 22, -80);
        scene.add(moonMesh);
    }

    /**
     * Natural Dark Rooftop Parapet and Contact Shadow (NO PLATFORM)
     */
    function buildRooftopAndMist() {
        rooftopGroup = new THREE.Group();

        // Dark matte weathered asphalt/stone rooftop corner
        const roofGeo = new THREE.BoxGeometry(22, 10, 22);
        const roofMat = new THREE.MeshStandardMaterial({
            color: 0x020408, // Pure deep nighttime rooftop asphalt
            roughness: 0.99,
            metalness: 0.02
        });
        const roofMesh = new THREE.Mesh(roofGeo, roofMat);
        roofMesh.position.set(isMobile ? 0 : 5.4, -7.8, 6.0);
        roofMesh.receiveShadow = true;
        rooftopGroup.add(roofMesh);

        // Stone parapet cap / ledge
        const capGeo = new THREE.BoxGeometry(22.4, 0.6, 22.4);
        const capMat = new THREE.MeshStandardMaterial({
            color: 0x03060c,
            roughness: 0.98,
            metalness: 0.02
        });
        const capMesh = new THREE.Mesh(capGeo, capMat);
        capMesh.position.set(isMobile ? 0 : 5.4, -2.8, 6.0);
        capMesh.receiveShadow = true;
        rooftopGroup.add(capMesh);

        // Soft circular contact shadow directly beneath the hero's contact points
        const shadowCanvas = document.createElement('canvas');
        shadowCanvas.width = 256;
        shadowCanvas.height = 256;
        const sCtx = shadowCanvas.getContext('2d');
        const sGrad = sCtx.createRadialGradient(128, 128, 10, 128, 128, 120);
        sGrad.addColorStop(0, 'rgba(0, 0, 0, 0.95)');
        sGrad.addColorStop(0.5, 'rgba(1, 2, 5, 0.6)');
        sGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        sCtx.fillStyle = sGrad;
        sCtx.fillRect(0, 0, 256, 256);

        const shadowTexture = new THREE.CanvasTexture(shadowCanvas);
        const shadowGeo = new THREE.PlaneGeometry(8, 8);
        const shadowMat = new THREE.MeshBasicMaterial({
            map: shadowTexture,
            transparent: true,
            opacity: 0.9,
            depthWrite: false
        });
        const contactShadow = new THREE.Mesh(shadowGeo, shadowMat);
        contactShadow.rotation.x = -Math.PI / 2;
        contactShadow.position.set(isMobile ? 0 : 5.4, -2.48, 6.2);
        rooftopGroup.add(contactShadow);

        scene.add(rooftopGroup);
    }

    /**
     * Exactly ONE Subtle Spider-Web Element Behind Hero
     * Thin, delicate, semi-transparent, partially emerging from shadow
     */
    function buildSingleSubtleSpiderWeb() {
        webGroup = new THREE.Group();

        const numSpokes = 12;
        const numRings = 7;
        const maxRadius = 8.5; // Concentrated behind the hero
        const vertices = [];

        // Radial Spokes
        for (let i = 0; i < numSpokes; i++) {
            const angle = (i / numSpokes) * Math.PI * 2;
            const cos = Math.cos(angle);
            const sin = Math.sin(angle);

            vertices.push(0, 0, 0);
            vertices.push(cos * maxRadius, sin * maxRadius, -1.0 + Math.sin(angle * 3) * 0.5);
        }

        // Concentric Rings with organic thread sag
        const ringPoints = [];
        for (let r = 1; r <= numRings; r++) {
            const rad = (r / numRings) * maxRadius;
            const pts = [];
            for (let i = 0; i <= numSpokes; i++) {
                const angle = ((i % numSpokes) / numSpokes) * Math.PI * 2;
                const cos = Math.cos(angle);
                const sin = Math.sin(angle);
                const zCurve = Math.sin(r * 0.8 + angle * 2) * 0.3;
                pts.push(new THREE.Vector3(cos * rad, sin * rad, zCurve));
            }
            ringPoints.push(pts);
        }

        for (let r = 0; r < ringPoints.length; r++) {
            const pts = ringPoints[r];
            for (let i = 0; i < pts.length - 1; i++) {
                vertices.push(pts[i].x, pts[i].y, pts[i].z);
                vertices.push(pts[i + 1].x, pts[i + 1].y, pts[i + 1].z);
            }
        }

        const webGeo = new THREE.BufferGeometry();
        webGeo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

        const webMat = new THREE.LineBasicMaterial({
            color: 0x4a7096,
            transparent: true,
            opacity: 0.14,
            blending: THREE.AdditiveBlending
        });

        const webMesh = new THREE.LineSegments(webGeo, webMat);
        webGroup.add(webMesh);

        // Position directly behind the hero's perched location
        webGroup.position.set(isMobile ? 0 : 5.4, 2.0, 3.5);
        webGroup.scale.set(1.0, 1.0, 1.0);
        scene.add(webGroup);
    }

    /**
     * Minimal Atmospheric Night Particles
     */
    function buildAtmosphericDust() {
        const count = isMobile ? 30 : 55;
        const positions = new Float32Array(count * 3);
        const sizes = new Float32Array(count);

        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 35;
            positions[i * 3 + 1] = -4 + Math.random() * 22;
            positions[i * 3 + 2] = -5 + Math.random() * 25;
            sizes[i] = 0.08 + Math.random() * 0.12;
        }

        const dustGeo = new THREE.BufferGeometry();
        dustGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const dustMat = new THREE.PointsMaterial({
            color: 0xa8c5e2,
            size: 0.14,
            transparent: true,
            opacity: 0.35,
            blending: THREE.AdditiveBlending
        });

        dustParticles = new THREE.Points(dustGeo, dustMat);
        scene.add(dustParticles);
    }

    /**
     * Hero Setup: Supports loading external GLTF asset (assets/spider_hero.glb)
     * or uses high-fidelity, sculpted cinematic Spider-Man crouch character
     */
    function buildHeroSystem() {
        heroGroup = new THREE.Group();
        heroGroup.position.set(isMobile ? 0 : 5.4, -0.6, 6.2);
        heroGroup.scale.set(1.45, 1.45, 1.45);
        scene.add(heroGroup);

        // Check for external 3D model (e.g. exported from Meshy or dropped in assets)
        const possibleAssetPaths = [
            'assets/spider_hero.glb',
            'assets/spiderman.glb',
            'assets/hero.glb',
            'assets/model.glb'
        ];

        let loadedExternal = false;

        if (typeof THREE.GLTFLoader !== 'undefined') {
            const loader = new THREE.GLTFLoader();

            function tryLoadAsset(index) {
                if (index >= possibleAssetPaths.length) {
                    if (!loadedExternal) {
                        buildCinematicSculptedHero();
                    }
                    return;
                }

                const path = possibleAssetPaths[index];
                loader.load(
                    path,
                    function (gltf) {
                        loadedExternal = true;
                        // Clear existing children if fallback was loaded
                        while (heroGroup.children.length > 0) {
                            heroGroup.remove(heroGroup.children[0]);
                        }

                        const model = gltf.scene;

                        // Calculate bounding box to normalize scale
                        const box = new THREE.Box3().setFromObject(model);
                        const size = new THREE.Vector3();
                        box.getSize(size);
                        const maxDim = Math.max(size.x, size.y, size.z);
                        const targetScale = 6.2 / maxDim;
                        model.scale.set(targetScale, targetScale, targetScale);

                        // Center model
                        const center = new THREE.Vector3();
                        box.getCenter(center);
                        model.position.x = -center.x * targetScale;
                        model.position.y = -box.min.y * targetScale - 1.5;
                        model.position.z = -center.z * targetScale;

                        // Enable shadows & cinematic PBR material settings
                        model.traverse(function (child) {
                            if (child.isMesh) {
                                child.castShadow = true;
                                child.receiveShadow = true;
                                if (child.material) {
                                    child.material.roughness = Math.max(0.35, child.material.roughness || 0.4);
                                }
                            }
                        });

                        heroGroup.add(model);
                    },
                    undefined,
                    function () {
                        // Error or not found, try next
                        tryLoadAsset(index + 1);
                    }
                );
            }

            tryLoadAsset(0);
        } else {
            buildCinematicSculptedHero();
        }
    }

    /**
     * High-Fidelity Sculpted Fallback Hero:
     * Organic, athletic Spider-Man in classic 3-point landing crouch pose:
     * - Sculpted athletic torso with broad shoulders and V-taper
     * - Seamless organic limbs with smooth joint caps (no floating chopped cylinders!)
     * - Sleek aerodynamic mask with clean comic-accurate white eye lenses and black bezels (no cage rings!)
     * - Iconic chest emblem & suit color division (crimson red & midnight cobalt blue)
     * - Planted right hand touching down, left arm raised in dynamic crouch tension
     * - Rich movie rim lighting response
     */
    function buildCinematicSculptedHero() {
        // Suit Materials: Rich cinematic Spider-Crimson & Midnight Suit Blue
        const spideyRedMat = new THREE.MeshStandardMaterial({
            color: 0xa81226, // Deep Spider Crimson
            roughness: 0.32,
            metalness: 0.15
        });

        const spideyBlueMat = new THREE.MeshStandardMaterial({
            color: 0x08162d, // Midnight Suit Blue
            roughness: 0.38,
            metalness: 0.22
        });

        const suitBlackMat = new THREE.MeshStandardMaterial({
            color: 0x111116,
            roughness: 0.5,
            metalness: 0.25
        });

        const lensReflectiveWhiteMat = new THREE.MeshStandardMaterial({
            color: 0xfafcff,
            roughness: 0.1,
            metalness: 0.35,
            emissive: 0x223344,
            emissiveIntensity: 0.15
        });

        // Helper: creates a seamless organic limb segment with spherical joint caps
        function createSmoothLimbSegment(radiusTop, radiusBottom, length, material) {
            const group = new THREE.Group();
            const cylinder = new THREE.Mesh(new THREE.CylinderGeometry(radiusTop, radiusBottom, length, 16), material);
            cylinder.castShadow = true;
            group.add(cylinder);

            // Top joint cap
            const topCap = new THREE.Mesh(new THREE.SphereGeometry(radiusTop, 14, 14), material);
            topCap.position.y = length / 2;
            group.add(topCap);

            // Bottom joint cap
            const bottomCap = new THREE.Mesh(new THREE.SphereGeometry(radiusBottom, 14, 14), material);
            bottomCap.position.y = -length / 2;
            group.add(bottomCap);

            return group;
        }

        // 1. Contoured Muscular Torso: V-taper angled forward in athletic crouch
        heroChest = new THREE.Group();
        heroChest.position.set(0, 0.35, 0.2);
        heroChest.rotation.x = 0.44; // Forward lean
        heroGroup.add(heroChest);

        // Core Torso contoured volume
        const torsoGeo = new THREE.CylinderGeometry(0.95, 0.62, 1.85, 18);
        const torsoMesh = new THREE.Mesh(torsoGeo, spideyRedMat);
        torsoMesh.castShadow = true;
        heroChest.add(torsoMesh);

        // Muscular Pectoral Definition (Left & Right)
        const pecGeo = new THREE.SphereGeometry(0.48, 14, 14);
        pecGeo.scale(0.9, 0.7, 0.45);

        const leftPec = new THREE.Mesh(pecGeo, spideyRedMat);
        leftPec.position.set(-0.38, 0.38, 0.68);
        leftPec.rotation.z = -0.12;
        heroChest.add(leftPec);

        const rightPec = new THREE.Mesh(pecGeo, spideyRedMat);
        rightPec.position.set(0.38, 0.38, 0.68);
        rightPec.rotation.z = 0.12;
        heroChest.add(rightPec);

        // Midnight Blue Side Flank Panels
        const flankGeo = new THREE.CylinderGeometry(0.96, 0.63, 1.8, 16, 1, true, Math.PI * 0.28, Math.PI * 0.44);
        const leftFlank = new THREE.Mesh(flankGeo, spideyBlueMat);
        heroChest.add(leftFlank);

        const rightFlank = new THREE.Mesh(flankGeo.clone(), spideyBlueMat);
        rightFlank.rotation.y = Math.PI;
        heroChest.add(rightFlank);

        // Iconic Spider Emblem on Chest
        const spiderCoreGeo = new THREE.SphereGeometry(0.12, 10, 10);
        spiderCoreGeo.scale(0.65, 1.4, 0.3);
        const spiderCore = new THREE.Mesh(spiderCoreGeo, suitBlackMat);
        spiderCore.position.set(0, 0.35, 0.88);
        heroChest.add(spiderCore);

        for (let i = 0; i < 4; i++) {
            const side = i < 2 ? -1 : 1;
            const legGeo = new THREE.TorusGeometry(0.32 + (i % 2) * 0.12, 0.022, 6, 16, Math.PI / 1.7);
            const leg = new THREE.Mesh(legGeo, suitBlackMat);
            leg.position.set(side * 0.25, 0.35 + (i % 2) * 0.16, 0.84);
            leg.rotation.z = side * (0.32 + (i % 2) * 0.6);
            heroChest.add(leg);
        }

        // 2. Sculpted Aerodynamic Mask & Comic Eyes
        heroHead = new THREE.Group();
        heroHead.position.set(0, 1.35, 0.45);
        heroHead.rotation.x = -0.28; // Tilted to face the viewer
        heroChest.add(heroHead);

        // Organic Head Geometry (smooth tapered jaw, aerodynamic cranium)
        const maskGeo = new THREE.SphereGeometry(0.8, 24, 22);
        maskGeo.scale(0.82, 1.14, 0.94);
        const maskMesh = new THREE.Mesh(maskGeo, spideyRedMat);
        maskMesh.castShadow = true;
        heroHead.add(maskMesh);

        // Sleek Comic-Accurate Spider Eyes (Left & Right)
        function createSpideyEye(isLeft) {
            const eyeGroup = new THREE.Group();

            // Sculpted Black Outer Contour
            const outerShape = new THREE.Shape();
            outerShape.moveTo(0, 0.38);
            outerShape.quadraticCurveTo(0.34, 0.12, 0.28, -0.3);
            outerShape.quadraticCurveTo(0.02, -0.2, -0.26, -0.12);
            outerShape.quadraticCurveTo(-0.22, 0.18, 0, 0.38);

            const outerGeo = new THREE.ShapeGeometry(outerShape);
            const outerMesh = new THREE.Mesh(outerGeo, suitBlackMat);

            // Reflective White Inner Lens
            const innerShape = new THREE.Shape();
            innerShape.moveTo(0, 0.32);
            innerShape.quadraticCurveTo(0.28, 0.1, 0.23, -0.24);
            innerShape.quadraticCurveTo(0.02, -0.16, -0.21, -0.09);
            innerShape.quadraticCurveTo(-0.18, 0.14, 0, 0.32);

            const innerGeo = new THREE.ShapeGeometry(innerShape);
            const innerMesh = new THREE.Mesh(innerGeo, lensReflectiveWhiteMat);
            innerMesh.position.z = 0.025;

            eyeGroup.add(outerMesh);
            eyeGroup.add(innerMesh);

            const flip = isLeft ? 1 : -1;
            eyeGroup.scale.set(flip * 0.85, 0.85, 0.85);
            eyeGroup.rotation.y = isLeft ? -0.34 : 0.34;
            eyeGroup.rotation.z = isLeft ? -0.1 : 0.1;
            eyeGroup.position.set(isLeft ? -0.34 : 0.34, 0.05, 0.74);
            return eyeGroup;
        }

        heroHead.add(createSpideyEye(true));
        heroHead.add(createSpideyEye(false));

        // 3. Right Arm: Reaching Down, Hand Planted on Rooftop
        rightArmPivot = new THREE.Group();
        rightArmPivot.position.set(0.95, 0.55, 0.1);
        heroChest.add(rightArmPivot);

        // Shoulder joint
        const rShoulder = new THREE.Mesh(new THREE.SphereGeometry(0.36, 16, 16), spideyRedMat);
        rightArmPivot.add(rShoulder);

        // Upper arm (Midnight blue)
        const rBicep = createSmoothLimbSegment(0.25, 0.22, 1.25, spideyBlueMat);
        rBicep.position.set(0.35, -0.55, 0.35);
        rBicep.rotation.x = -0.58;
        rBicep.rotation.z = -0.42;
        rightArmPivot.add(rBicep);

        // Forearm & Gauntlet (Crimson red)
        const rForearm = createSmoothLimbSegment(0.23, 0.19, 1.35, spideyRedMat);
        rForearm.position.set(0.65, -1.5, 0.95);
        rForearm.rotation.x = -1.15;
        rForearm.rotation.z = -0.25;
        rightArmPivot.add(rForearm);

        // Planted Hand touching the rooftop
        const rHand = new THREE.Group();
        rHand.position.set(0.72, -2.1, 1.55);
        rForearm.add(rHand);

        const palm = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.12, 0.34), spideyRedMat);
        rHand.add(palm);

        // Curved fingers making contact with stone surface
        for (let f = -0.11; f <= 0.11; f += 0.07) {
            const finger = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.035, 0.34, 6), spideyRedMat);
            finger.position.set(f, -0.05, 0.2);
            finger.rotation.x = 0.65;
            rHand.add(finger);
        }

        // 4. Left Arm: Dynamic athletic crouch poise (raised high, elbow cocked)
        leftArmPivot = new THREE.Group();
        leftArmPivot.position.set(-0.95, 0.55, 0.1);
        heroChest.add(leftArmPivot);

        const lShoulder = new THREE.Mesh(new THREE.SphereGeometry(0.36, 16, 16), spideyRedMat);
        leftArmPivot.add(lShoulder);

        const lBicep = createSmoothLimbSegment(0.25, 0.22, 1.25, spideyBlueMat);
        lBicep.position.set(-0.45, 0.25, -0.42);
        lBicep.rotation.x = 0.85;
        lBicep.rotation.z = 0.55;
        leftArmPivot.add(lBicep);

        const lForearm = createSmoothLimbSegment(0.23, 0.19, 1.3, spideyRedMat);
        lForearm.position.set(-0.85, 0.95, -0.85);
        lForearm.rotation.x = 1.35;
        lForearm.rotation.z = 0.35;
        leftArmPivot.add(lForearm);

        const lFist = new THREE.Mesh(new THREE.SphereGeometry(0.24, 12, 12), spideyRedMat);
        lFist.position.set(-1.05, 1.45, -1.2);
        leftArmPivot.add(lFist);

        // 5. Crouched Legs: Supporting the athletic landing
        // Right Leg (bent closely underneath)
        const rThigh = createSmoothLimbSegment(0.38, 0.3, 1.6, spideyBlueMat);
        rThigh.position.set(0.75, -0.7, 0.1);
        rThigh.rotation.x = 1.32;
        rThigh.rotation.z = 0.42;
        heroGroup.add(rThigh);

        const rCalf = createSmoothLimbSegment(0.32, 0.26, 1.55, spideyRedMat);
        rCalf.position.set(1.15, -1.35, 0.85);
        rCalf.rotation.x = -1.05;
        rCalf.rotation.z = -0.28;
        heroGroup.add(rCalf);

        // Left Leg (extended outward in classic dramatic spider crouch)
        const lThigh = createSmoothLimbSegment(0.38, 0.3, 1.7, spideyBlueMat);
        lThigh.position.set(-0.88, -0.6, -0.25);
        lThigh.rotation.x = 1.15;
        lThigh.rotation.z = -0.72;
        heroGroup.add(lThigh);

        const lCalf = createSmoothLimbSegment(0.32, 0.26, 1.65, spideyRedMat);
        lCalf.position.set(-1.55, -1.25, 0.3);
        lCalf.rotation.x = -0.82;
        lCalf.rotation.z = 0.42;
        heroGroup.add(lCalf);

        const lBoot = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.22, 0.65), spideyRedMat);
        lBoot.position.set(-1.68, -1.95, 0.75);
        heroGroup.add(lBoot);
    }

    /**
     * Mouse Movement & Horizontal Drag-to-Rotate Interaction
     */
    function setupInteractionListeners() {
        window.addEventListener('resize', onWindowResize);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('scroll', onScroll, { passive: true });

        const heroViewport = document.querySelector('.spider-hero-viewport');
        const dragHint = document.getElementById('dragRotateHint');

        // Drag to rotate character (Mouse & Touch)
        function startDrag(clientX) {
            isDragging = true;
            dragStartX = clientX;
            dismissDragHint();
        }

        function moveDrag(clientX) {
            if (!isDragging) return;
            const deltaX = clientX - dragStartX;
            dragStartX = clientX;
            targetHeroRotationY += deltaX * 0.0075;
        }

        function endDrag() {
            isDragging = false;
        }

        function dismissDragHint() {
            if (!hasInteractedWithRotation) {
                hasInteractedWithRotation = true;
                if (dragHint) {
                    dragHint.classList.add('fading');
                    setTimeout(() => dragHint.remove(), 600);
                }
            }
        }

        if (canvas) {
            canvas.addEventListener('mousedown', (e) => startDrag(e.clientX));
            window.addEventListener('mousemove', (e) => {
                if (isDragging) moveDrag(e.clientX);
            });
            window.addEventListener('mouseup', endDrag);

            // Touch events
            canvas.addEventListener('touchstart', (e) => {
                if (e.touches.length > 0) startDrag(e.touches[0].clientX);
            }, { passive: true });

            window.addEventListener('touchmove', (e) => {
                if (isDragging && e.touches.length > 0) moveDrag(e.touches[0].clientX);
            }, { passive: true });

            window.addEventListener('touchend', endDrag);
        }

        if (heroViewport) {
            heroViewport.addEventListener('mousedown', (e) => {
                if (!e.target.closest('a, button, input, textarea')) {
                    startDrag(e.clientX);
                }
            });
        }
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
        isMobile = window.innerWidth < 992;

        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);

        updateCameraPosition();

        if (heroGroup) {
            heroGroup.position.x = isMobile ? 0 : 5.4;
            heroGroup.scale.set(isMobile ? 1.2 : 1.45, isMobile ? 1.2 : 1.45, isMobile ? 1.2 : 1.45);
        }
        if (webGroup) {
            webGroup.position.x = isMobile ? 0 : 5.4;
        }
        if (rooftopGroup) {
            rooftopGroup.position.x = isMobile ? 0 : 5.4;
        }
    }

    /**
     * Cinematic Animation Loop:
     * - Subtle idle breathing
     * - Damped drag rotation
     * - Smooth mouse parallax (head tracking & camera sway)
     * - Subtle scroll zoom & push
     */
    function animate() {
        requestAnimationFrame(animate);

        const delta = clock.getDelta();
        const time = clock.getElapsedTime();

        // 1. Mouse Lerping (smooth & subtle)
        const lerpFactor = isReducedMotion ? 0.01 : 0.04;
        mouse.x += (mouse.targetX - mouse.x) * lerpFactor;
        mouse.y += (mouse.targetY - mouse.y) * lerpFactor;

        // 2. Drag-to-Rotate Damping
        heroRotationY += (targetHeroRotationY - heroRotationY) * 0.08;

        // 3. Idle Character Breathing & Stance
        const breath = Math.sin(time * 1.6) * 0.022;

        if (heroChest) {
            heroChest.position.y = 0.45 + breath;
            heroChest.scale.set(1 + breath * 0.4, 1 + breath * 0.4, 1 + breath * 0.4);
        }

        // 4. Subtle Look-At Tracking
        if (heroHead) {
            heroHead.rotation.y = mouse.x * 0.28 + Math.sin(time * 0.6) * 0.03;
            heroHead.rotation.x = -0.32 - mouse.y * 0.18;
        }

        // 5. Apply Drag Rotation + Idle Sway to Hero Group
        if (heroGroup) {
            heroGroup.rotation.y = heroRotationY + Math.sin(time * 0.4) * 0.02;
        }

        // 6. Camera Parallax & Scroll Transition
        if (!isReducedMotion) {
            // Subtle camera sway with mouse
            camera.position.x += ((isMobile ? 0 : mouse.x * 0.6) - camera.position.x) * 0.04;
            camera.position.y += ((1.8 - mouse.y * 0.4) - camera.position.y) * 0.04;

            // Scroll zoom: smoothly push camera back as user leaves hero
            const scrollZOffset = scrollProgress * 10;
            camera.position.z = (isMobile ? 23 : 20) + scrollZOffset;
        }

        // 7. Cursor light tracking
        if (cursorLight) {
            cursorLight.position.x = mouse.x * 8 + 3;
            cursorLight.position.y = -mouse.y * 5 + 3;
        }

        // 8. Subtle Web Sway
        if (webGroup) {
            webGroup.rotation.z = Math.sin(time * 0.25) * 0.03;
            webGroup.position.x = (isMobile ? 0 : 5.4) + mouse.x * 0.15;
            webGroup.position.y = 2.2 - mouse.y * 0.12;
        }

        // 9. Distant Skyline Subtle Parallax
        if (cityGroup) {
            cityGroup.position.x = -mouse.x * 1.2;
            cityGroup.position.y = mouse.y * 0.6;
        }

        // 10. Atmospheric Dust Motes Drift
        if (dustParticles) {
            dustParticles.rotation.y = time * 0.015;
            const positions = dustParticles.geometry.attributes.position.array;
            for (let i = 1; i < positions.length; i += 3) {
                positions[i] += Math.sin(time + i) * 0.003;
            }
            dustParticles.geometry.attributes.position.needsUpdate = true;
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
