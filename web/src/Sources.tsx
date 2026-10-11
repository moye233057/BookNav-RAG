import type { Citation } from "./api";

type SourcesProps = {
  citations: Citation[];
};

function formatPages(pages: number[]): string {
  if (pages.length === 0) {
    return "";
  }
  return `第 ${pages.join("、")} 页`;
}

export function Sources({ citations }: SourcesProps) {
  return (
    <aside className="sidebar" aria-label="参考资料">
      <h2 className="sidebar-title">参考资料</h2>
      <div className="sidebar-body">
        {citations.length === 0 ? (
          <p className="empty">还没有参考资料</p>
        ) : (
          <ul className="citation-list">
            {citations.map((citation) => (
              <li key={citation.id} className="citation">
                <p className="citation-meta">
                  {citation.source} {formatPages(citation.pages)}
                </p>
                <p className="citation-snippet">{citation.snippet}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
