/**
 * dashboard_script.js
 * SIENNA AI - Neural Dashboard Logic (updated)
 * - Presets are locked (non-editable) when applied.
 * - "Create New" enables editing.
 * - IDs s1..s8 used for sliders.
 * - Click a preset: highlight it, switch to Characters tab, apply preset.
 */

document.addEventListener('DOMContentLoaded', () => {

    // 1. --- Tab Switching Logic ---
    const tabs = {
        stats: document.getElementById('sec-stats'),
        chars: document.getElementById('sec-chars')
    };

    const btns = {
        stats: document.getElementById('tab-stats'),
        chars: document.getElementById('tab-chars')
    };

    window.switchTab = (tabName) => {
        Object.values(tabs).forEach(tab => tab && tab.classList.add('hidden'));
        Object.values(btns).forEach(btn => btn && btn.classList.remove('active'));
        if (tabs[tabName]) tabs[tabName].classList.remove('hidden');
        if (btns[tabName]) btns[tabName].classList.add('active');
        localStorage.setItem('sienna_last_tab', tabName);
    };

    const lastTab = localStorage.getItem('sienna_last_tab') || 'stats';
    switchTab(lastTab);


    // 2. --- 3-Dots Menu Logic ---
    const menuTrigger = document.getElementById('menu-trigger');
    if (menuTrigger) {
        menuTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            menuTrigger.classList.toggle('active');
        });
    }

    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('settings-dropdown');
        if (dropdown && menuTrigger && !dropdown.contains(e.target) && !menuTrigger.contains(e.target)) {
            menuTrigger.classList.remove('active');
        }
    });


    // 3. --- Character Presets Data (locked by default) ---
    const characterPresets = [
        { name: "Sienna", desc: "The Original: Funny & Balanced", curiosity: 60, sensitivity: 50, intelligence: 85, kindness: 70, happiness: 80, sadness: 15, boldness: 40, shyness: 30, locked: true },
        { name: "Roxy", desc: "Bratty: Bold, Teasing & Wild", curiosity: 90, sensitivity: 20, intelligence: 70, kindness: 30, happiness: 95, sadness: 5, boldness: 100, shyness: 0, locked: true },
        { name: "Laila", desc: "Melancholic: Deep & Sensitive", curiosity: 40, sensitivity: 90, intelligence: 80, kindness: 85, happiness: 20, sadness: 80, boldness: 10, shyness: 90, locked: true },
        { name: "Maya", desc: "Genius: Highly Curious & Smart", curiosity: 100, sensitivity: 40, intelligence: 100, kindness: 60, happiness: 50, sadness: 10, boldness: 50, shyness: 40, locked: true },
        { name: "Sarah", desc: "Typical: Normal Egyptian Girl", curiosity: 50, sensitivity: 50, intelligence: 60, kindness: 70, happiness: 60, sadness: 20, boldness: 40, shyness: 50, locked: true },
        { name: "Luna", desc: "Shy: Quiet & Extremely Intelligent", curiosity: 30, sensitivity: 75, intelligence: 95, kindness: 90, happiness: 40, sadness: 30, boldness: 5, shyness: 100, locked: true },
        { name: "Raven", desc: "Dark: Bold, Cold & Sarcastic", curiosity: 60, sensitivity: 10, intelligence: 85, kindness: 20, happiness: 30, sadness: 60, boldness: 90, shyness: 10, locked: true },
        { name: "Zara", desc: "Hyper: Very Happy & Energetic", curiosity: 80, sensitivity: 40, intelligence: 50, kindness: 80, happiness: 100, sadness: 0, boldness: 70, shyness: 20, locked: true },
        { name: "Ivy", desc: "Seductress: Bold & Playful", curiosity: 85, sensitivity: 30, intelligence: 75, kindness: 40, happiness: 85, sadness: 10, boldness: 95, shyness: 5, locked: true },
        { name: "Cleo", desc: "Elegant: Kind & Respectful", curiosity: 50, sensitivity: 60, intelligence: 90, kindness: 100, happiness: 70, sadness: 10, boldness: 30, shyness: 60, locked: true }
    ];

    const presetsList = document.getElementById('presets-list');

    // Helper to enable/disable form inputs
    const setEditable = (editable) => {
        const botName = document.getElementById('bot_name');
        const langSelect = document.getElementById('lang');
        const presetBadge = document.getElementById('preset-locked');

        if (botName) botName.disabled = !editable;
        if (langSelect) langSelect.disabled = !editable;
        // sliders s1..s8
        for (let i = 1; i <= 8; i++) {
            const s = document.getElementById('s' + i);
            if (s) s.disabled = !editable;
        }
        // sex_mode checkbox - find by name
        const sexCb = document.querySelector('input[name="sex_mode"]');
        if (sexCb) sexCb.disabled = !editable;

        if (presetBadge) {
            if (!editable) presetBadge.classList.remove('hidden');
            else presetBadge.classList.add('hidden');
        }
    };

    // Apply preset: fill fields and lock editing
    window.applyPreset = (char) => {
        const botNameEl = document.getElementById('bot_name');
        if (botNameEl) botNameEl.value = char.name;

        const fields = ['curiosity', 'sensitivity', 'intelligence', 'kindness', 'happiness', 'sadness', 'boldness', 'shyness'];
        fields.forEach((field, index) => {
            const slider = document.getElementById(`s${index + 1}`);
            const valLabel = document.getElementById(`v${index + 1}`);
            if (slider) {
                slider.value = char[field];
                // trigger oninput update (some browsers require explicit event)
                slider.dispatchEvent(new Event('input'));
                if (valLabel) valLabel.innerText = char[field] + '%';
            }
        });

        // lock inputs if preset.locked===true
        if (char.locked) {
            setEditable(false);
        } else {
            setEditable(true);
        }

        // set sex_mode to off for presets by default (you can change if needed)
        const sexCb = document.querySelector('input[name="sex_mode"]');
        if (sexCb) sexCb.checked = false;
    };

    // Utility: clear selected class from all preset buttons
    const clearPresetSelection = () => {
        if (!presetsList) return;
        presetsList.querySelectorAll('.char-item').forEach(el => el.classList.remove('selected'));
    };

    // Load Presets into Sidebar (with selectable highlight)
    if (presetsList) {
        characterPresets.forEach(char => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.dataset.name = char.name;
            btn.className = 'char-item w-full text-left p-4 rounded-2xl bg-white/5 border border-white/5 hover:border-purple-500/50 transition-all group flex justify-between items-center';
            btn.innerHTML = `
                <div>
                    <p class="font-bold text-sm group-hover:text-purple-400 transition">${char.name}</p>
                    <p class="text-[10px] text-gray-500 uppercase font-black tracking-tighter">${char.desc}</p>
                </div>
                <div class="text-xs ${char.locked ? 'text-yellow-300' : 'text-green-300'} font-black">${char.locked ? 'LOCKED' : 'CUSTOM'}</div>
            `;
            btn.addEventListener('click', (e) => {
                // visual selection
                clearPresetSelection();
                btn.classList.add('selected');

                // switch to chars tab and apply the preset
                switchTab('chars');
                applyPreset(char);
            });
            presetsList.appendChild(btn);
        });
    }

    // Create new character: reset fields and enable editing
    window.createNewChar = () => {
        clearPresetSelection();
        const botName = document.getElementById('bot_name');
        if (botName) botName.value = "New Identity";
        const lang = document.getElementById('lang');
        if (lang) lang.value = 'ar';
        for (let i = 1; i <= 8; i++) {
            const s = document.getElementById('s' + i);
            const v = document.getElementById('v' + i);
            if (s) s.value = 50;
            if (v) v.innerText = '50%';
        }
        const sexCb = document.querySelector('input[name="sex_mode"]');
        if (sexCb) sexCb.checked = false;
        // enable editing
        setEditable(true);
        // show Characters tab
        switchTab('chars');
    };


    // 4. --- Real-time Slider Value Update ---
    window.updateRange = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val + '%';
    };


    // 5. --- Toast Notification Handler ---
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('success')) {
        const toast = document.getElementById('toast');
        if (toast) {
            toast.style.transform = "translateX(0)";
            document.querySelectorAll('.stat-card').forEach(card => {
                card.classList.add('animate__animated', 'animate__pulse');
            });
            setTimeout(() => {
                toast.style.transform = "translateX(200%)";
                window.history.replaceState({}, document.title, window.location.pathname);
            }, 4000);
        }
    }

    // Initialize: disable editing if current bot is one of the locked presets (Sienna)
    const initNameEl = document.getElementById('bot_name');
    const initName = initNameEl ? initNameEl.value || '' : '';
    const isLockedInitial = characterPresets.some(p => p.locked && p.name.toLowerCase() === initName.toLowerCase());
    if (isLockedInitial) setEditable(false);

});

console.log("%c SIENNA DASHBOARD INITIALIZED ", "background: #10B981; color: #fff; padding: 5px; font-weight: bold;");