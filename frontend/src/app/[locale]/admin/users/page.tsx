'use client';

import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useNotifications } from '@/contexts/NotificationContext';
import { useI18n, useT } from '@/i18n/useTranslations';

interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'viewer';
  status: 'active' | 'inactive' | 'suspended';
  lastLogin: string;
  createdAt: string;
  predictionsCount: number;
}

const mockUsers: User[] = [
  {
    id: '1',
    name: 'أحمد محمد',
    email: 'ahmed@example.com',
    role: 'admin',
    status: 'active',
    lastLogin: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
    predictionsCount: 45,
  },
  {
    id: '2',
    name: 'فاطمة علي',
    email: 'fatima@example.com',
    role: 'user',
    status: 'active',
    lastLogin: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
    predictionsCount: 12,
  },
  {
    id: '3',
    name: 'خالد سعيد',
    email: 'khalid@example.com',
    role: 'user',
    status: 'inactive',
    lastLogin: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    createdAt: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    predictionsCount: 8,
  },
];

export default function UsersManagementPage() {
  const { locale } = useI18n();
  const t = useT();
  const isAr = locale === 'ar';
  const { addNotification } = useNotifications();
  const [users, setUsers] = useState<User[]>(mockUsers);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRole, setFilterRole] = useState<'all' | 'admin' | 'user' | 'viewer'>('all');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive' | 'suspended'>('all');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showModal, setShowModal] = useState(false);

  const filteredUsers = users.filter((user) => {
    if (searchQuery && !user.name.includes(searchQuery) && !user.email.includes(searchQuery))
      return false;
    if (filterRole !== 'all' && user.role !== filterRole) return false;
    if (filterStatus !== 'all' && user.status !== filterStatus) return false;
    return true;
  });

  const handleStatusChange = useCallback(
    (userId: string, newStatus: User['status']) => {
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, status: newStatus } : u))
      );
      addNotification({
        type: 'success',
        title: isAr ? 'تم التحديث' : 'Updated',
        message: isAr ? 'تم تحديث حالة المستخدم بنجاح' : 'User status updated successfully',
        duration: 3000,
      });
    },
    [addNotification]
  );

  const handleRoleChange = useCallback(
    (userId: string, newRole: User['role']) => {
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u)));
      addNotification({
        type: 'success',
        title: isAr ? 'تم التحديث' : 'Updated',
        message: isAr ? 'تم تحديث صلاحيات المستخدم بنجاح' : 'User role updated successfully',
        duration: 3000,
      });
    },
    [addNotification]
  );

  const handleDelete = useCallback(
    (userId: string) => {
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      addNotification({
        type: 'success',
        title: isAr ? 'تم الحذف' : 'Deleted',
        message: isAr ? 'تم حذف المستخدم بنجاح' : 'User deleted successfully',
        duration: 3000,
      });
    },
    [addNotification]
  );

  return (
    <main className="section" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="container space-y-8">
        <header className="space-y-3">
          <h1 className="text-3xl font-extrabold text-ink-900 dark:text-white sm:text-4xl">
            {t.users.title}
          </h1>
          <p className="text-base leading-relaxed text-slate-600 dark:text-slate-300">
            {t.users.subtitle}
          </p>
        </header>

        <div className="card p-6 space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-ink-900 dark:text-white">
                {t.users.search}
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={isAr ? 'اسم أو بريد إلكتروني' : 'Name or email'}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm placeholder:text-slate-400 focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white dark:placeholder:text-slate-400"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-ink-900 dark:text-white">
                {t.users.role}
              </label>
                    <select
                      value={filterRole}
                      onChange={(e) => setFilterRole(e.target.value as 'all' | 'admin' | 'user' | 'viewer')}
                      className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
                    >
                      <option value="all">{t.users.all_roles}</option>
                      <option value="admin">{t.users.role_admin}</option>
                      <option value="user">{t.users.role_user}</option>
                      <option value="viewer">{t.users.role_viewer}</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-ink-900 dark:text-white">
                      {t.users.status}
                    </label>
                    <select
                      value={filterStatus}
                      onChange={(e) => setFilterStatus(e.target.value as 'all' | 'active' | 'inactive' | 'suspended')}
                className="w-full px-4 py-2 rounded-xl border border-slate-200 bg-white text-ink-900 shadow-sm focus:border-raboo3-400 focus:ring-raboo3-400 dark:border-white/10 dark:bg-ink-900/50 dark:text-white"
              >
                <option value="all">{t.users.all_statuses}</option>
                <option value="active">{t.users.status_active}</option>
                <option value="inactive">{t.users.status_inactive}</option>
                <option value="suspended">{t.users.status_suspended}</option>
              </select>
            </div>
          </div>
        </div>

        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 dark:bg-ink-900/50">
                <tr>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">
                    {t.users.name}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">
                    {t.users.role}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">
                    {t.users.status}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">
                    {t.users.last_login}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">
                    {t.users.predictions}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">
                    {t.users.actions}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {filteredUsers.map((user) => (
                  <motion.tr
                    key={user.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="hover:bg-slate-50 dark:hover:bg-ink-900/30"
                  >
                    <td className="px-6 py-4">
                      <div>
                        <div className="font-semibold text-ink-900 dark:text-white">{user.name}</div>
                        <div className="text-sm text-slate-600 dark:text-slate-400">{user.email}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.id, e.target.value as User['role'])}
                        className="px-3 py-1 text-sm rounded-lg border border-slate-200 bg-white text-ink-900 focus:border-raboo3-400 dark:border-slate-700 dark:bg-ink-900/50 dark:text-white"
                      >
                        <option value="admin">{t.users.role_admin}</option>
                        <option value="user">{t.users.role_user}</option>
                        <option value="viewer">{t.users.role_viewer}</option>
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        value={user.status}
                        onChange={(e) => handleStatusChange(user.id, e.target.value as User['status'])}
                        className={`px-3 py-1 text-sm rounded-lg border ${
                          user.status === 'active'
                            ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300'
                            : user.status === 'suspended'
                              ? 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300'
                              : 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900/20 dark:text-slate-300'
                        }`}
                      >
                        <option value="active">{t.users.status_active}</option>
                        <option value="inactive">{t.users.status_inactive}</option>
                        <option value="suspended">{t.users.status_suspended}</option>
                      </select>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-400">
                      {new Date(user.lastLogin).toLocaleDateString(locale === 'ar' ? 'ar-SA' : 'en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-raboo3-100 text-raboo3-700 dark:bg-raboo3-900/30 dark:text-raboo3-300">
                        {user.predictionsCount}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            setSelectedUser(user);
                            setShowModal(true);
                          }}
                          className="btn border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 text-xs px-3 py-1 dark:border-slate-700 dark:bg-ink-900/50 dark:text-slate-300"
                        >
                          {t.users.details}
                        </button>
                        <button
                          onClick={() => handleDelete(user.id)}
                          className="btn border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 text-xs px-3 py-1 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"
                        >
                          {t.users.delete}
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {showModal && selectedUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="card p-6 max-w-md w-full space-y-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-bold text-ink-900 dark:text-white">{t.users.user_details}</h3>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-slate-600 dark:text-slate-400 hover:text-ink-900 dark:hover:text-white"
                >
                  ×
                </button>
              </div>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-slate-600 dark:text-slate-400">{t.users.name}</span>
                  <span className="font-semibold text-ink-900 dark:text-white mr-2">
                    {selectedUser.name}
                  </span>
                </div>
                <div>
                  <span className="text-slate-600 dark:text-slate-400">{t.users.email}</span>
                  <span className="font-semibold text-ink-900 dark:text-white mr-2">
                    {selectedUser.email}
                  </span>
                </div>
                <div>
                  <span className="text-slate-600 dark:text-slate-400">{t.users.registration_date}</span>
                  <span className="font-semibold text-ink-900 dark:text-white mr-2">
                    {new Date(selectedUser.createdAt).toLocaleDateString(locale === 'ar' ? 'ar-SA' : 'en-US')}
                  </span>
                </div>
                <div>
                  <span className="text-slate-600 dark:text-slate-400">{t.users.predictions}:</span>
                  <span className="font-semibold text-ink-900 dark:text-white mr-2">
                    {selectedUser.predictionsCount}
                  </span>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </main>
  );
}

