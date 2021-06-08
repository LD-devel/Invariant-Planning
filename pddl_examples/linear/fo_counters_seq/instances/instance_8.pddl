;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_2)
  (:domain fn-counters)
  (:objects
    c0 - counter
  )

  (:init
    (= (max_int) 92)
        (= (value c0) 0)

        (= (rate_value c0) 1)
  )

  (:goal (and
    (>= (value c0) 92)
  ))
)
