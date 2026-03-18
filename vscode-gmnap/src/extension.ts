import * as vscode from 'vscode';

const NARROW_NBSP = '\u202F';
const REGULAR_SPACE = ' ';

// GMNAP name fields where narrow NBSP toggle applies
const NAME_FIELDS = ['CanonicalLatin', 'CanonicalNative', 'AlternativeLatin'];

export function activate(context: vscode.ExtensionContext) {
    // Register the narrow NBSP toggle command
    const toggleCmd = vscode.commands.registerCommand('gmnap.toggleNarrowNbsp', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const document = editor.document;
        const edits: vscode.TextEdit[] = [];
        let toggleCount = 0;

        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i);
            const text = line.text;

            // Check if this line contains a name field
            const isNameField = NAME_FIELDS.some(field =>
                text.trimStart().startsWith(`${field}:`)
            );

            if (!isNameField) continue;

            // Extract the value part (after the colon)
            const colonIdx = text.indexOf(':');
            if (colonIdx < 0) continue;

            const valuePart = text.substring(colonIdx + 1);

            // Determine toggle direction based on current content
            let newValue: string;
            if (valuePart.includes(NARROW_NBSP)) {
                // Narrow NBSP -> regular space
                newValue = valuePart.replace(new RegExp(NARROW_NBSP, 'g'), REGULAR_SPACE);
            } else {
                // Regular space -> narrow NBSP (only between name parts, not leading whitespace)
                const trimmed = valuePart.trimStart();
                const leading = valuePart.substring(0, valuePart.length - trimmed.length);

                // Handle quoted strings
                let inner = trimmed;
                let quoteChar = '';
                if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
                    (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
                    quoteChar = trimmed[0];
                    inner = trimmed.slice(1, -1);
                }

                // Replace spaces between name components with narrow NBSP
                // But preserve comma-space patterns (e.g., "Family, Given")
                const replaced = inner.replace(/(?<=\S) (?=\S)/g, NARROW_NBSP);

                newValue = quoteChar
                    ? `${leading}${quoteChar}${replaced}${quoteChar}`
                    : `${leading}${replaced}`;
            }

            if (newValue !== valuePart) {
                const range = new vscode.Range(
                    i, colonIdx + 1,
                    i, text.length
                );
                edits.push(vscode.TextEdit.replace(range, newValue));
                toggleCount++;
            }
        }

        if (edits.length > 0) {
            const edit = new vscode.WorkspaceEdit();
            edit.set(document.uri, edits);
            vscode.workspace.applyEdit(edit).then(() => {
                const direction = edits[0].newText.includes(NARROW_NBSP)
                    ? 'narrow NBSP'
                    : 'regular space';
                vscode.window.showInformationMessage(
                    `GMNAP: Toggled ${toggleCount} name field(s) to ${direction}`
                );
            });
        } else {
            vscode.window.showInformationMessage('GMNAP: No name fields found to toggle');
        }
    });

    context.subscriptions.push(toggleCmd);

    // Wire YAML schema validation if redhat.vscode-yaml is installed
    const yamlExt = vscode.extensions.getExtension('redhat.vscode-yaml');
    if (yamlExt) {
        const config = vscode.workspace.getConfiguration('yaml');
        const schemas = config.get<Record<string, string | string[]>>('schemas') || {};
        const schemaPath = vscode.workspace.getConfiguration('gmnap').get<string>('schemaPath', 'docs/schema_v2.0.json');

        if (!schemas[schemaPath]) {
            schemas[schemaPath] = ['out/yaml/*.yaml'];
            config.update('schemas', schemas, vscode.ConfigurationTarget.Workspace);
        }
    }
}

export function deactivate() {}
