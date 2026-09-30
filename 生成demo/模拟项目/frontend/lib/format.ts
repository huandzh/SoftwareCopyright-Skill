// 展示层格式化工具：统一数字、时间、文件大小和金额的写法

export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const pad = (input: number) => String(input).padStart(2, "0");
  return (
    date.getFullYear() +
    "-" +
    pad(date.getMonth() + 1) +
    "-" +
    pad(date.getDate()) +
    " " +
    pad(date.getHours()) +
    ":" +
    pad(date.getMinutes())
  );
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "0 秒";
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  if (minutes <= 0) {
    return rest + " 秒";
  }
  return minutes + " 分 " + rest + " 秒";
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  // 小于 10 的数值保留一位小数，便于阅读 1.5 GB 这类容量
  return (value < 10 && index > 0 ? value.toFixed(1) : Math.round(value)) + " " + units[index];
}

export function formatCurrency(amount: number): string {
  if (!Number.isFinite(amount)) {
    return "¥0.00";
  }
  return "¥" + amount.toFixed(2);
}

export function formatPercent(value: number, digits = 0): string {
  if (!Number.isFinite(value)) {
    return "0%";
  }
  return (value * 100).toFixed(digits) + "%";
}

export function truncate(value: string, max = 40): string {
  const text = String(value ?? "");
  if (text.length <= max) {
    return text;
  }
  return text.slice(0, max - 1) + "…";
}
