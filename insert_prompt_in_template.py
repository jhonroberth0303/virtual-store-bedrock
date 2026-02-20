import sys
import os

TEMPLATE_PATH = 'template.yml'
PROMPT_PATH = os.path.join('prompts', 'prompt-ecomm.txt')



def main():
    # Leer el prompt
    with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
        prompt_text = f.read().rstrip()
    # Leer el template
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Buscar la línea de Instruction: |
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('Instruction: |'):
            start_idx = i
            break
    if start_idx is None:
        print('No se encontró Instruction: | en el template.')
        sys.exit(1)

    # Encontrar el final del bloque indentado
    indent_len = len(lines[start_idx + 1]) - len(lines[start_idx + 1].lstrip()) if (start_idx + 1) < len(lines) else 8
    end_idx = start_idx + 1
    while end_idx < len(lines):
        line = lines[end_idx]
        if line.strip() == '' or (len(line) - len(line.lstrip())) >= indent_len:
            end_idx += 1
        else:
            break

    # Indentar el prompt para YAML
    indent = ' ' * indent_len
    prompt_yaml = [(indent + l if l else indent) + '\n' for l in prompt_text.splitlines()]

    # Reconstruir el template
    new_lines = lines[:start_idx + 1] + prompt_yaml + lines[end_idx:]
    with open(TEMPLATE_PATH, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Prompt insertado en {TEMPLATE_PATH} correctamente.")

if __name__ == '__main__':
    main()
