# Admin Access Request Validation Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent invalid Admin access applications in the browser and show a useful message when the backend returns a 422 validation response.

**Architecture:** Keep password confirmation as form-only state and preserve the existing Admin API request type. Add Ant Design cross-field and trimmed-length validation in the page, and isolate backend error formatting in an exported pure helper that can be unit tested without rendering the page.

**Tech Stack:** React, TypeScript, Ant Design Form, Umi request, Vitest.

## Global Constraints

- Do not change the backend `AdminAccessRequestCreateRequest` schema.
- Do not send `password_confirm` in the request payload.
- Keep Umi `request`; do not introduce React Query or axios.
- Public Admin access request calls remain unauthenticated with `withCredentials: false`.
- Never include password values in errors or diagnostics.
- Write and observe each failing test before changing production code.

---

## File Structure

- Modify `frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.ts`: hold form-only confirmation state and normalize the API payload.
- Modify `frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.test.ts`: verify payload omission, form validation wiring, and 422 formatting.
- Modify `frontend/intent-routing-console/src/pages/AdminAccessRequest/index.tsx`: render confirmation and aligned access-reason rules, and expose the pure error formatter.

### Task 1: Password Confirmation And Backend-Compatible Form Validation

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.ts`
- Modify: `frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/AdminAccessRequest/index.tsx`

**Interfaces:**
- Consumes: `API.AdminAccessRequestCreateRequest` and Ant Design `Form.Item` validation.
- Produces: `AdminAccessRequestFormValues.password_confirm: string`; `toAdminAccessRequestCreateRequest(values): API.AdminAccessRequestCreateRequest` that omits confirmation.

- [ ] **Step 1: Write failing tests for form-only confirmation and validation wiring**

Update the existing normalization fixture with `password_confirm` and add focused source-contract assertions:

```ts
expect(
  toAdminAccessRequestCreateRequest({
    user_number: ' 21P0031 ',
    name: ' 홍길동 ',
    department_id: ' dept-001 ',
    email: ' Admin.User@Example.com ',
    password: 'secret-passphrase',
    password_confirm: 'secret-passphrase',
    access_reason: ' Need Admin UI access for onboarding ',
  }),
).toEqual({
  user_number: '21P0031',
  name: '홍길동',
  department_id: 'dept-001',
  email: 'Admin.User@Example.com',
  password: 'secret-passphrase',
  access_reason: 'Need Admin UI access for onboarding',
});

it('requires matching password confirmation and a trimmed ten-character reason', () => {
  const source = requestPageSource();

  expect(source).toContain('name="password_confirm"');
  expect(source).toContain("dependencies={['password']}");
  expect(source).toContain("getFieldValue('password')");
  expect(source).toContain("value.trim().length < 10");
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/pages/AdminAccessRequest/requestForm.test.ts
```

Expected: FAIL because `password_confirm` is not part of `AdminAccessRequestFormValues` and the page has no confirmation or trimmed 10-character rule.

- [ ] **Step 3: Add form-only state and minimal page validation**

Add the form-only field without changing the API type:

```ts
export type AdminAccessRequestFormValues = {
  user_number: string;
  name: string;
  department_id: string;
  email: string;
  password: string;
  password_confirm: string;
  access_reason: string;
};
```

Insert this item immediately after the password field:

```tsx
<Form.Item
  label="비밀번호 확인"
  name="password_confirm"
  dependencies={['password']}
  rules={[
    { required: true, message: '비밀번호를 다시 입력해 주세요.' },
    ({ getFieldValue }) => ({
      validator(_, value) {
        if (!value || getFieldValue('password') === value) return Promise.resolve();
        return Promise.reject(new Error('비밀번호가 일치하지 않습니다.'));
      },
    }),
  ]}
>
  <Input.Password autoComplete="new-password" />
</Form.Item>
```

Replace the access-reason rules with required and trimmed minimum validation:

```tsx
rules={[
  { required: true, message: '접근 사유를 입력해 주세요.' },
  {
    validator: (_, value) =>
      !value || value.trim().length >= 10
        ? Promise.resolve()
        : Promise.reject(new Error('접근 사유는 10자 이상 입력해 주세요.')),
  },
]}
```

Keep `toAdminAccessRequestCreateRequest` unchanged so its explicit return object omits `password_confirm`.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/pages/AdminAccessRequest/requestForm.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit the isolated form-validation change**

```bash
git add frontend/intent-routing-console/src/pages/AdminAccessRequest/index.tsx frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.ts frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.test.ts
git commit -m "fix: validate admin access request form"
```

### Task 2: Readable FastAPI 422 Validation Errors

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/AdminAccessRequest/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.test.ts`

**Interfaces:**
- Consumes: Umi request errors with `response.data` or `data`, including `detail: Array<{ loc?: unknown[]; msg?: string }>`.
- Produces: `adminAccessRequestErrorMessage(error: unknown): string` for the form-level Alert.

- [ ] **Step 1: Write a failing unit test for a representative 422 response**

Import the helper from the page and add:

```ts
import AdminAccessRequestPage, { adminAccessRequestErrorMessage } from './index';

it('shows the first useful FastAPI validation detail', () => {
  expect(
    adminAccessRequestErrorMessage({
      response: {
        data: {
          detail: [
            {
              loc: ['body', 'access_reason'],
              msg: 'String should have at least 10 characters',
            },
          ],
        },
      },
    }),
  ).toBe('access_reason: String should have at least 10 characters');
});
```

Retain the default page import assertion only if required by TypeScript; otherwise omit the unused default import.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/pages/AdminAccessRequest/requestForm.test.ts
```

Expected: FAIL because `adminAccessRequestErrorMessage` is not exported.

- [ ] **Step 3: Implement the minimal safe error formatter**

Replace the local formatter with:

```ts
type ValidationDetail = {
  loc?: unknown[];
  msg?: unknown;
};

export const adminAccessRequestErrorMessage = (error: any) => {
  const payload = error?.response?.data ?? error?.data;
  const detail = payload?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const first = detail.find(
      (item: ValidationDetail) => typeof item?.msg === 'string',
    ) as ValidationDetail | undefined;
    if (first && typeof first.msg === 'string') {
      const field = Array.isArray(first.loc) ? first.loc.at(-1) : undefined;
      return typeof field === 'string' ? `${field}: ${first.msg}` : first.msg;
    }
  }
  if (detail?.error?.message) return detail.error.message;
  if (payload?.error?.message) return payload.error.message;
  return error?.message ?? '신청을 제출하지 못했습니다.';
};
```

Update the catch block to call `adminAccessRequestErrorMessage(err)`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
cd frontend/intent-routing-console
pnpm vitest run src/pages/AdminAccessRequest/requestForm.test.ts src/services/authServices.test.ts
```

Expected: both test files PASS.

- [ ] **Step 5: Run type and project-policy verification**

Run:

```bash
cd frontend/intent-routing-console
pnpm run typecheck
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" src/pages/AdminAccessRequest/index.tsx src/pages/AdminAccessRequest/requestForm.ts src/pages/AdminAccessRequest/requestForm.test.ts
```

Expected: typecheck PASS and `rg` returns no matches.

- [ ] **Step 6: Commit the error-formatting change**

```bash
git add frontend/intent-routing-console/src/pages/AdminAccessRequest/index.tsx frontend/intent-routing-console/src/pages/AdminAccessRequest/requestForm.test.ts
git commit -m "fix: show admin request validation errors"
```
