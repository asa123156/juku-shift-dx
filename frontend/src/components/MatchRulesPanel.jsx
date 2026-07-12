import React, { useMemo } from 'react';

export const DEFAULT_WEEKLY_LIMITS = {
  国語: 1,
  数学: 2,
  英語: 0,
  理科: 0,
  社会: 0,
};

export const DEFAULT_MATCH_RULES = {
  no_gaps: true,
  weekly_limits: { ...DEFAULT_WEEKLY_LIMITS },
};

const MATH_SUBJECTS = new Set(['数学', '算数', '数学I', '数学II']);
const SCIENCE_SUBJECTS = new Set(['理科', '物理', '化学']);

export function normalizeSubject(subject) {
  if (MATH_SUBJECTS.has(subject)) return '数学';
  if (SCIENCE_SUBJECTS.has(subject)) return '理科';
  return subject;
}

export function collectSubjects(students, weeklyLimits) {
  const set = new Set(Object.keys(weeklyLimits ?? {}));
  (students ?? []).forEach((s) => {
    (s.subjects ?? []).forEach((sub) => set.add(normalizeSubject(sub)));
  });
  return [...set].sort((a, b) => a.localeCompare(b, 'ja'));
}

function RuleToggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="rounded border-gray-300"
      />
      <span>{label}</span>
    </label>
  );
}

export function MatchRulesPanel({ rules, onChange, subjects }) {
  const setLimit = (subject, raw) => {
    const val = raw === '' ? 0 : Math.max(0, parseInt(raw, 10) || 0);
    onChange({
      ...rules,
      weekly_limits: { ...rules.weekly_limits, [subject]: val },
    });
  };

  const subjectList = useMemo(
    () => collectSubjects([], rules.weekly_limits),
    [rules.weekly_limits],
  );

  const displaySubjects = subjects?.length ? subjects : subjectList;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4">
      <div className="flex flex-wrap items-center gap-4 mb-3">
        <span className="text-sm font-bold text-gray-700">マッチングルール</span>
        <RuleToggle
          label="空きコマなし（生徒・講師とも途中に空きを残さない／無理なら無視して埋める）"
          checked={rules.no_gaps}
          onChange={(v) => onChange({ ...rules, no_gaps: v })}
        />
      </div>
      <div>
        <p className="text-xs text-gray-500 mb-2">科目ごとの週コマ上限（0＝制限なし）</p>
        <div className="flex flex-wrap gap-3">
          {displaySubjects.map((subject) => (
            <label key={subject} className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm">
              <span className="font-bold min-w-[3rem]">{subject}</span>
              <span className="text-gray-400 text-xs">週</span>
              <input
                type="number"
                min={0}
                max={20}
                value={rules.weekly_limits?.[subject] ?? 0}
                onChange={(e) => setLimit(subject, e.target.value)}
                className="w-14 border border-gray-300 rounded px-2 py-1 text-center font-bold"
              />
              <span className="text-gray-400 text-xs">コマ</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
