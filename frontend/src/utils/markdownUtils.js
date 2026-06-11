/**
 * Extracts alternating text and table blocks from raw markdown text.
 */
export function extractBlocks(text) {
  if (!text) return [];
  const parts = [];
  const lines = text.split('\n');
  let currentText = [];
  let currentTable = [];
  let inTable = false;

  for (let line of lines) {
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      if (!inTable) {
        if (currentText.length > 0) {
          parts.push({ type: 'text', content: currentText.join('\n') });
          currentText = [];
        }
        inTable = true;
      }
      currentTable.push(line);
    } else {
      if (inTable) {
        parts.push({ type: 'table', lines: currentTable });
        currentTable = [];
        inTable = false;
      }
      currentText.push(line);
    }
  }
  
  if (currentText.length > 0) parts.push({ type: 'text', content: currentText.join('\n') });
  if (currentTable.length > 0) parts.push({ type: 'table', lines: currentTable });
  
  return parts;
}

/**
 * Lightweight markdown -> HTML for assistant messages.
 * Handles **bold**, *italic*, bullet lists, and preserves format.
 */
export function renderMarkdown(text) {
  if (!text) return '';

  let html = text
    // escape angle brackets (safety)
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // headers ### text
    .replace(/^(#{1,6})\s+(.*)$/gm, (match, hashes, content) => {
      const level = hashes.length;
      return `<h${level} class="ai-chat-heading">${content}</h${level}>`;
    })
    // bold **text**
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // italic *text*
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
    // line breaks
    .replace(/\n/g, '<br/>');

  // Convert bullet lines (- item or * item) into <ul><li>
  const lines = html.split('<br/>');
  let inList = false;
  const processed = [];

  for (const line of lines) {
    const bulletMatch = line.match(/^\s*[-*]\s+(.+)/);
    if (bulletMatch) {
      if (!inList) { processed.push('<ul>'); inList = true; }
      processed.push(`<li>${bulletMatch[1]}</li>`);
    } else {
      if (inList) { processed.push('</ul>'); inList = false; }
      processed.push(line);
    }
  }
  if (inList) processed.push('</ul>');

  return processed.join(inList ? '' : '<br/>');
}
