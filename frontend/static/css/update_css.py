import re

with open('style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Add light mode variables
content = content.replace('''    /* GLOWS */
    --glow-green: 0 0 10px rgba(5, 150, 105, 0.3);
    --glow-blue: 0 0 10px rgba(2, 132, 199, 0.3);
    --glow-red: 0 0 10px rgba(225, 29, 72, 0.3);
}''', '''    /* GLOWS */
    --glow-green: 0 0 10px rgba(5, 150, 105, 0.3);
    --glow-blue: 0 0 10px rgba(2, 132, 199, 0.3);
    --glow-red: 0 0 10px rgba(225, 29, 72, 0.3);

    /* COMPONENT BACKGROUNDS & COLORS - LIGHT */
    --body-grad1: rgba(2, 132, 199, 0.05);
    --body-grad2: rgba(5, 150, 105, 0.05);
    --scrollbar-thumb: #CBD5E1;
    --scrollbar-thumb-hover: #94A3B8;
    --header-bg: rgba(255, 255, 255, 0.8);
    --sidebar-bg: rgba(255, 255, 255, 0.95);
    --avatar-grad1: #E2E8F0;
    --avatar-grad2: #FFFFFF;
    --brand-text1: #111827;
    --brand-text2: #4B5563;
    --menu-hover: rgba(0, 0, 0, 0.05);
    --menu-active-bg: rgba(2, 132, 199, 0.08);
    --menu-active-border: rgba(2, 132, 199, 0.15);
    --menu-active-shadow: rgba(2, 132, 199, 0.05);
    --flow-node-bg: #FFFFFF;
    --flow-line: #D1D5DB;
    --alert-bg: rgba(0, 0, 0, 0.03);
    --alert-crit-bg: rgba(225, 29, 72, 0.1);
    --alert-crit-color: #BE123C;
    --alert-warn-bg: rgba(217, 119, 6, 0.1);
    --alert-warn-color: #B45309;
    --alert-succ-bg: rgba(5, 150, 105, 0.1);
    --alert-succ-color: #047857;
    --clock-bg: rgba(5, 150, 105, 0.05);
    --clock-border: rgba(5, 150, 105, 0.2);
    --login-bg1: #FFFFFF;
    --login-bg2: #F3F4F6;
    --auth-card-bg: rgba(255, 255, 255, 0.8);
    --form-input-bg: #F9FAFB;
}''')

# Add dark mode variables
content = content.replace('''    /* GLOWS */
    --glow-green: 0 0 10px rgba(0, 255, 157, 0.4);
    --glow-blue: 0 0 10px rgba(0, 212, 255, 0.4);
    --glow-red: 0 0 10px rgba(255, 0, 85, 0.4);
}''', '''    /* GLOWS */
    --glow-green: 0 0 10px rgba(0, 255, 157, 0.4);
    --glow-blue: 0 0 10px rgba(0, 212, 255, 0.4);
    --glow-red: 0 0 10px rgba(255, 0, 85, 0.4);

    /* COMPONENT BACKGROUNDS & COLORS - DARK */
    --body-grad1: rgba(0, 212, 255, 0.05);
    --body-grad2: rgba(0, 255, 157, 0.05);
    --scrollbar-thumb: #30363D;
    --scrollbar-thumb-hover: #50555e;
    --header-bg: rgba(14, 17, 23, 0.8);
    --sidebar-bg: rgba(14, 17, 23, 0.95);
    --avatar-grad1: #1f242d;
    --avatar-grad2: #0d1117;
    --brand-text1: #fff;
    --brand-text2: #8B949E;
    --menu-hover: rgba(255, 255, 255, 0.03);
    --menu-active-bg: rgba(0, 212, 255, 0.08);
    --menu-active-border: rgba(0, 212, 255, 0.15);
    --menu-active-shadow: rgba(0, 212, 255, 0.05);
    --flow-node-bg: rgba(30, 35, 41, 0.8);
    --flow-line: #30363D;
    --alert-bg: rgba(255, 255, 255, 0.03);
    --alert-crit-bg: rgba(255, 0, 85, 0.1);
    --alert-crit-color: #ffb3b3;
    --alert-warn-bg: rgba(250, 255, 0, 0.05);
    --alert-warn-color: #ffffff;
    --alert-succ-bg: rgba(0, 255, 157, 0.05);
    --alert-succ-color: #ccffeb;
    --clock-bg: rgba(0, 255, 157, 0.05);
    --clock-border: rgba(0, 255, 157, 0.2);
    --login-bg1: #1b2028;
    --login-bg2: #050608;
    --auth-card-bg: rgba(22, 27, 34, 0.8);
    --form-input-bg: #0d1117;
}''')

# Replace usages
replacements = [
    (
        '''    background-image:\n        radial-gradient(circle at 10% 20%, rgba(0, 212, 255, 0.05) 0%, transparent 40%),\n        radial-gradient(circle at 90% 80%, rgba(0, 255, 157, 0.05) 0%, transparent 40%);''',
        '''    background-image:\n        radial-gradient(circle at 10% 20%, var(--body-grad1) 0%, transparent 40%),\n        radial-gradient(circle at 90% 80%, var(--body-grad2) 0%, transparent 40%);'''
    ),
    ('''    background: #30363D;''', '''    background: var(--scrollbar-thumb);'''),
    ('''    background: #50555e;''', '''    background: var(--scrollbar-thumb-hover);'''),
    ('''    background: rgba(14, 17, 23, 0.8);''', '''    background: var(--header-bg);'''),
    ('''    background: rgba(0, 255, 157, 0.05);\n    padding: 5px 10px;\n    border-radius: 4px;\n    border: 1px solid rgba(0, 255, 157, 0.2);''', '''    background: var(--clock-bg);\n    padding: 5px 10px;\n    border-radius: 4px;\n    border: 1px solid var(--clock-border);'''),
    ('''    background: linear-gradient(135deg, #1f242d, #0d1117);''', '''    background: linear-gradient(135deg, var(--avatar-grad1), var(--avatar-grad2));'''),
    ('''    background: rgba(14, 17, 23, 0.95);''', '''    background: var(--sidebar-bg);'''),
    ('''    background: linear-gradient(90deg, #fff, #8B949E);''', '''    background: linear-gradient(90deg, var(--brand-text1), var(--brand-text2));'''),
    ('''    background: rgba(255, 255, 255, 0.03);''', '''    background: var(--menu-hover);'''),
    ('''    background: rgba(0, 212, 255, 0.08);\n    color: var(--neon-blue);\n    border: 1px solid rgba(0, 212, 255, 0.15);\n    box-shadow: 0 0 15px rgba(0, 212, 255, 0.05);''', '''    background: var(--menu-active-bg);\n    color: var(--neon-blue);\n    border: 1px solid var(--menu-active-border);\n    box-shadow: 0 0 15px var(--menu-active-shadow);'''),
    ('''    background: rgba(30, 35, 41, 0.8);''', '''    background: var(--flow-node-bg);'''),
    ('''    background: #30363D;''', '''    background: var(--flow-line);'''),
    ('''    background: rgba(255, 255, 255, 0.03);''', '''    background: var(--alert-bg);'''),
    ('''    color: #ffb3b3;\n    background: rgba(255, 0, 85, 0.1);''', '''    color: var(--alert-crit-color);\n    background: var(--alert-crit-bg);'''),
    ('''    color: #ffffff;\n    background: rgba(250, 255, 0, 0.05);''', '''    color: var(--alert-warn-color);\n    background: var(--alert-warn-bg);'''),
    ('''    color: #ccffeb;\n    background: rgba(0, 255, 157, 0.05);''', '''    color: var(--alert-succ-color);\n    background: var(--alert-succ-bg);'''),
    ('''    background: radial-gradient(circle at center, #1b2028 0%, #050608 100%);''', '''    background: radial-gradient(circle at center, var(--login-bg1) 0%, var(--login-bg2) 100%);'''),
    ('''    background: rgba(22, 27, 34, 0.8);''', '''    background: var(--auth-card-bg);'''),
    ('''    background: #0d1117;''', '''    background: var(--form-input-bg);'''),
]

for old, new in replacements:
    content = content.replace(old, new)

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("CSS updated successfully!")
