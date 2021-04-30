(define (problem security-clearance-4-2)

	(:domain security-clearance)

	(:init
 		(not (clear_d1_l1) )
 		(not (clear_d1_l2) )
 		(not (clear_d2_l1) )
 		(not (clear_d2_l2) )
 		(not (clear_d3_l1) )
 		(not (clear_d3_l2) )
 		(not (clear_d4_l1) )
 		(not (clear_d4_l2) )
		(= (cost_d1) 0)
 		(= (priority_d1) 1)
 		(= (high) 2)
 		(= (low) 1)
 		(= (cost_d2) 0)
 		(= (priority_d2) 1)
 		(= (high) 2)
 		(= (low) 1)
 		(= (cost_d3) 0)
 		(= (priority_d3) 1)
 		(= (high) 2)
 		(= (low) 1)
 		(= (cost_d4) 0)
 		(= (priority_d4) 1)
 		(= (high) 2)
 		(= (low) 1)
	)

	(:goal (and
 		(clear_d1_l1 )
 		(clear_d1_l2 )
 		(clear_d2_l1 )
 		(clear_d2_l2 )
 		(clear_d3_l1 )
 		(clear_d3_l2 )
 		(clear_d4_l1 )
 		(clear_d4_l2 ))
	)

	(:metric minimize (+ (cost_d2) (+ (cost_d3) (+ (cost_d4)  (cost_d1)))))

)