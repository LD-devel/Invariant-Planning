(define (problem instance_3_2)
  (:domain fo-counters-rnd)
  (:objects

    c0 c1 c2  - counter
  )

  (:init
    
    (= (max_int) 6)
        (= (value c0) 1)
        (= (value c1) 2)
        (= (value c2) 0)

        (= (rate_value c0) 0)
        (= (rate_value c1) 0)
        (= (rate_value c2) 0)
    )

  (:goal (and

    (<= (+ (value c0) 1) (value c1))
    (<= (+ (value c1) 1) (value c2))))
)