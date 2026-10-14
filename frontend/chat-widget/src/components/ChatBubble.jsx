function renderFormattedMessage(text, isUser) {
  if (!text) return null;

  // 1. Normalize inline bullets and section headers into clean line breaks
  const normalized = text
    .replace(/\s+-\s+/g, "\n- ")
    .replace(/([a-zA-Z0-9])\.?\s+(\*\*[A-Z][^*]+?\*\*)/g, "$1.\n\n$2")
    .replace(/([.!?])\s+(If you need|Please note|For more information|Feel free to)/gi, "$1\n\n$2");

  const lines = normalized.split(/\r?\n/);

  return lines.map((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return <div key={idx} style={{ height: 6 }} />;
    }

    const isBullet = /^[-*•]\s+/.test(trimmed);
    const content = isBullet ? trimmed.replace(/^[-*•]\s+/, "") : line;

    // Parse bold markdown **...** into <strong> elements
    const parts = [];
    const boldRegex = /\*\*([^*]+?)\*\*/g;
    let lastIndex = 0;
    let match;

    while ((match = boldRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        // Strip any residual stray asterisks
        const textBefore = content.substring(lastIndex, match.index).replace(/\*\*/g, "");
        if (textBefore) parts.push(textBefore);
      }
      parts.push(
        <strong key={`${idx}-${match.index}`} style={{ fontWeight: 600 }}>
          {match[1]}
        </strong>
      );
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < content.length) {
      const textAfter = content.substring(lastIndex).replace(/\*\*/g, "");
      if (textAfter) parts.push(textAfter);
    }

    const lineElements = parts.length > 0 ? parts : content.replace(/\*\*/g, "");

    if (isBullet) {
      return (
        <div
          key={idx}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 6,
            margin: "3px 0 3px 4px",
          }}
        >
          <span
            style={{
              color: isUser ? "rgba(255,255,255,0.7)" : "#64748b",
              userSelect: "none",
              lineHeight: 1.45,
            }}
          >
            •
          </span>
          <div style={{ flex: 1, lineHeight: 1.45 }}>{lineElements}</div>
        </div>
      );
    }

    return (
      <div key={idx} style={{ margin: "2px 0", lineHeight: 1.45 }}>
        {lineElements}
      </div>
    );
  });
}

export function ChatBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 10,
      }}
    >
      <div
        style={{
          maxWidth: "80%",
          padding: "9px 14px",
          borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
          background: isUser ? "#1A3C5E" : "#f1f5f9",
          color: isUser ? "#fff" : "#1e293b",
          fontSize: 14,
          lineHeight: 1.5,
          wordBreak: "break-word",
        }}
      >
        {renderFormattedMessage(message.text, isUser)}
      </div>
    </div>
  );
}