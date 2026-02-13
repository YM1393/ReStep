// Utility functions

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('ko-KR');
}

export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('ko-KR');
}

export function calculateAge(birthDate: string): number {
  const today = new Date();
  const birth = new Date(birthDate);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
}

export function getSpeedAssessment(speed: number): string {
  if (speed >= 1.2) return 'Normal';
  if (speed >= 1.0) return 'Mildly reduced';
  if (speed >= 0.8) return 'Moderately reduced';
  return 'Severely reduced';
}

export function getSpeedColor(speed: number): string {
  if (speed >= 1.2) return 'green';
  if (speed >= 0.8) return 'yellow';
  return 'red';
}
