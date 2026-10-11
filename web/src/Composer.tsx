import type { FormEvent, KeyboardEvent } from "react";
import type { FilterTag } from "./api";

type ComposerProps = {
  draft: string;
  tags: FilterTag[];
  isAsking: boolean;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
};

function tagLabel(field: string): string {
  if (field === "source") {
    return "来源";
  }
  return field;
}

export function Composer({
  draft,
  tags,
  isAsking,
  onDraftChange,
  onSubmit,
}: ComposerProps) {
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  }

  return (
    <form
      className="composer"
      onSubmit={(event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      {tags.length === 0 ? null : (
        <div className="tag-row" aria-label="本轮检索用到的来源与标签">
          {tags.map((tag) => (
            <span key={`${tag.field}-${tag.value}`} className="tag-chip">
              {tagLabel(tag.field)} {tag.value}
            </span>
          ))}
        </div>
      )}
      <label className="composer-label" htmlFor="ask-input">
        问题
      </label>
      <textarea
        id="ask-input"
        className="composer-input"
        rows={3}
        value={draft}
        disabled={isAsking}
        placeholder="输入问题"
        onChange={(event) => onDraftChange(event.target.value)}
        onKeyDown={onKeyDown}
      />
      <button className="ask-button" type="submit" disabled={isAsking || draft.trim() === ""}>
        {isAsking ? "提问中" : "提问"}
      </button>
    </form>
  );
}
