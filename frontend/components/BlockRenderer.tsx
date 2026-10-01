"use client";

import { useEffect, useRef } from "react";
import styles from "./BlockRenderer.module.css";
import CodeLab from "./CodeLab";

// Dynamically load Prism for syntax highlighting
declare global {
  interface Window { Prism: any; }
}

interface Block {
  type: string;
  content?: string;
  language?: string;
  url?: string;
  caption?: string;
  src?: string;
  alt?: string;
}

function MarkdownBlock({ content }: { content: string }) {
  // Simple inline markdown: bold, inline code, line breaks
  const html = content
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.*?)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br/>");
  return (
    <p
      className={styles.markdown}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function CodeBlock({ content, language }: { content: string; language?: string }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (ref.current && window.Prism) window.Prism.highlightElement(ref.current);
  }, [content]);

  return (
    <div className={styles.codeWrapper}>
      {language && <span className={styles.langBadge}>{language}</span>}
      <pre className={styles.pre}>
        <code ref={ref} className={`language-${language || "text"}`}>
          {content}
        </code>
      </pre>
    </div>
  );
}

function YoutubeBlock({ url, caption }: { url: string; caption?: string }) {
  // Extract video ID from any YT URL format
  const match = url.match(/(?:v=|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  const videoId = match ? match[1] : null;
  if (!videoId) return null;
  return (
    <figure className={styles.videoFigure}>
      <div className={styles.videoWrapper}>
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${videoId}`}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          title={caption || "Video"}
        />
      </div>
      {caption && <figcaption className={styles.caption}>{caption}</figcaption>}
    </figure>
  );
}

function CalloutBlock({ content }: { content: string }) {
  return (
    <div className={styles.callout}>
      <span className={styles.calloutIcon}>💡</span>
      <p>{content}</p>
    </div>
  );
}

export default function BlockRenderer({ blocks }: { blocks: Block[] }) {
  if (!blocks || blocks.length === 0)
    return <p className={styles.empty}>No content yet.</p>;

  return (
    <div className={styles.container}>
      {blocks.map((block, i) => {
        switch (block.type) {
          case "markdown":
          case "text":
            return <MarkdownBlock key={i} content={block.content || ""} />;
          case "code":
            return (
              <CodeBlock key={i} content={block.content || ""} language={block.language} />
            );
          case "code_lab":
            return (
              <CodeLab key={i} initialCode={block.content || ""} language={block.language || "text"} />
            );
          case "youtube_video":
            return <YoutubeBlock key={i} url={block.url || ""} caption={block.caption} />;
          case "callout":
            return <CalloutBlock key={i} content={block.content || ""} />;
          case "image":
            return (
              <figure key={i} className={styles.imageFigure}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={block.src} alt={block.alt || ""} className={styles.image} />
                {block.caption && <figcaption className={styles.caption}>{block.caption}</figcaption>}
              </figure>
            );
          default:
            return null;
        }
      })}
    </div>
  );
}
