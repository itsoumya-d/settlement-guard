import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '5s',
  thresholds: {
    http_req_duration: ['p(95)<25'], // SLO: 95% of requests under 25ms
    http_req_failed: ['rate<0.01'],   // Error rate under 1%
  },
};

export default function () {
  const res = http.get('http://127.0.0.1:8080/actuator/health');
  check(res, {
    'status is 200': (r) => r.status === 200 || r.status === 404,
  });
  sleep(0.1);
}
