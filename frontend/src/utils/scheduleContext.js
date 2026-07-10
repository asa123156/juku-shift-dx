import { apiFetch } from './apiClient';

export async function fetchScheduleContext(date) {
  const query = date ? `?date=${encodeURIComponent(date)}` : '';
  const res = await apiFetch(`/api/calendar/schedule-context${query}`);
  if (!res.ok) {
    throw new Error('スケジュール情報の取得に失敗しました');
  }
  return res.json();
}

export function monthScheduleQuery(ctx) {
  if (ctx?.mode !== 'regular') return '';
  return `&calendar_year=${ctx.calendar_year}&month=${ctx.month}`;
}

export function shiftMonth(ctx, delta) {
  let year = ctx.calendar_year;
  let month = ctx.month + delta;
  if (month < 1) {
    month = 12;
    year -= 1;
  } else if (month > 12) {
    month = 1;
    year += 1;
  }
  return { calendar_year: year, month };
}

export function formatMonthLabel(year, month) {
  return `${year}年${month}月`;
}
