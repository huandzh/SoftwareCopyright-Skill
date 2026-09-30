import { LIMITS } from "./constants";

// 表单校验：返回错误信息数组，空数组表示通过
export function validateProjectName(name: string): string[] {
  const issues: string[] = [];
  const value = name.trim();
  if (!value) {
    issues.push("项目名称不能为空。");
  } else if (value.length > LIMITS.projectNameMax) {
    issues.push(`项目名称不能超过 ${LIMITS.projectNameMax} 个字符。`);
  }
  return issues;
}

export function validateIdea(idea: string): string[] {
  const issues: string[] = [];
  const value = idea.trim();
  if (value.length < LIMITS.ideaMin) {
    issues.push("创意描述太短，至少写一句话。");
  } else if (value.length > LIMITS.ideaMax) {
    issues.push(`创意描述不能超过 ${LIMITS.ideaMax} 个字符。`);
  }
  return issues;
}

export function validateChatMessage(content: string): string[] {
  const issues: string[] = [];
  if (!content.trim()) {
    issues.push("请输入内容后再发送。");
  } else if (content.length > LIMITS.messageMax) {
    issues.push(`单条指令不能超过 ${LIMITS.messageMax} 个字符。`);
  }
  return issues;
}

export function validateEmail(email: string): string[] {
  const value = email.trim();
  if (!value) {
    return ["请填写邮箱。"];
  }
  // 只做基本格式校验，真实有效性由后端确认
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value) ? [] : ["邮箱格式不正确。"];
}

export function validatePassword(password: string): string[] {
  const issues: string[] = [];
  if (password.length < 8) {
    issues.push("密码至少 8 位。");
  }
  const classes = [
    /[a-z]/.test(password),
    /[A-Z]/.test(password),
    /[0-9]/.test(password),
    /[^a-zA-Z0-9]/.test(password),
  ].filter(Boolean).length;
  if (classes < 2) {
    issues.push("密码需要包含字母、数字或符号中的两类。");
  }
  return issues;
}

export function validateShotCount(count: number): string[] {
  if (!Number.isFinite(count) || count <= 0) {
    return ["镜头数量必须大于 0。"];
  }
  if (count > LIMITS.shotsPerProject) {
    return [`单个项目最多 ${LIMITS.shotsPerProject} 个镜头。`];
  }
  return [];
}
