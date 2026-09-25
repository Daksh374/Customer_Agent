# Roles and Permissions

TaskFlow uses roles to control what people can see and do. There are workspace-level roles and project-level permissions.

## Workspace roles

**Owner** — The single person with full control of the workspace. Only the owner can delete the workspace, transfer ownership, and change the plan (unless a Billing admin is assigned).

**Admin** — Can manage members, integrations, security settings, and all projects. Admins can see every public and private project in the workspace on Business and Enterprise plans.

**Billing admin** — An add-on permission that can be given to any Admin or Member. Allows viewing invoices, updating payment methods, and changing plans without full admin rights.

**Member** — The standard role. Members can create projects, join public projects, and collaborate on tasks. They cannot manage workspace settings or other members.

**Guest** — Limited access for clients, contractors, or partners. Guests can only see projects they've been explicitly invited to and cannot browse the workspace directory. Guests are free (up to 5 per paid seat).

## Project permissions

Each project has its own access settings:

- **Public to workspace:** Every Member can find and join the project.
- **Private:** Only invited people can see the project.

Within a project, each person has one of these permission levels:

| Level | View | Comment | Edit tasks | Manage project |
|---|---|---|---|---|
| Viewer | ✓ | | | |
| Commenter | ✓ | ✓ | | |
| Editor | ✓ | ✓ | ✓ | |
| Project admin | ✓ | ✓ | ✓ | ✓ |

Project admins can change project settings, add or remove people, archive the project, and delete it.

## Changing someone's role

Workspace roles are changed by admins from **Admin → Members → ⋯ → Change role**. Project permissions are changed from **Project → Share**. Changes take effect immediately.

## Advanced permissions (Business and Enterprise)

- **Restrict project creation** to admins only.
- **Restrict guest invites** so only admins can add guests.
- **Custom field locking** to prevent members from editing specific fields.
- **Permission templates** to apply standard access settings to new projects.

## Common permission questions

**Why can't I see a project my teammate mentioned?** It's probably private. Ask a project admin to add you.

**Why can't I delete a task?** Only the task creator, project admins, and workspace admins can delete tasks. Editors can archive tasks instead.

**Can a guest see other guests?** No. Guests see only the members of projects they're invited to.

**Can admins read private projects?** On Pro, private projects are visible only to members. On Business and Enterprise, workspace admins can access all projects for compliance purposes, and each access is recorded in the audit log.
