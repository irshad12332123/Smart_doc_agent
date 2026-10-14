import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownViewProps {
  content: string;
  streaming?: boolean;
}

export function MarkdownView({ content, streaming }: MarkdownViewProps) {
  if (!content) {
    if (streaming) {
      return (
        <span className="streaming-placeholder">
          Searching academic knowledge base…
          <span className="streaming-cursor" />
        </span>
      );
    }
    return null;
  }

  return (
    <div className="markdown-renderer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
          code: ({ node, className, children, ...props }) => {
            const isInline =
              !className &&
              typeof children === "string" &&
              !children.includes("\n");
            return isInline ? (
              <code className="inline-code" {...props}>
                {children}
              </code>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
      {streaming && <span className="streaming-cursor" />}
    </div>
  );
}
